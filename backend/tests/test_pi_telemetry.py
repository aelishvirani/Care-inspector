"""Isolated signed Pi telemetry tests: no hardware or legacy WebSocket."""
import base64
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app import pi_telemetry_api
from backend.app.collectors import RegisteredCollector
from backend.app.models import (
    Alert, Customer, Device, DeviceConfiguration, Measurement, User,
)
from backend.app.pi_cloud_challenges import PiCloudChallenge
from backend.app.pi_pairing import PiPairingAttempt
from backend.app.pi_registered_devices import PiRegisteredDevice
from backend.app.pi_signed_discovery import collector_id_for_pi
from backend.app.printer_discovery_links import PrinterDiscoveryLink


class PiTelemetryTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        for model in (
            User, Customer, Device, DeviceConfiguration, Measurement, Alert,
            PiPairingAttempt, PiRegisteredDevice, PiCloudChallenge,
            RegisteredCollector, PrinterDiscoveryLink,
        ):
            model.__table__.create(self.engine)
        self.session = sessionmaker(bind=self.engine, autoflush=False)
        self.patch = patch.object(pi_telemetry_api, "SessionLocal", self.session)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.addCleanup(self.engine.dispose)
        app = FastAPI()
        app.include_router(pi_telemetry_api.router)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.key = Ed25519PrivateKey.generate()
        self.hardware_id = "pi-00000000abcdef12"
        self.device_id = "hitachi-test-1001"
        self.now = datetime.now(timezone.utc).replace(microsecond=0)
        with self.session() as db:
            db.add(PiRegisteredDevice(
                hardware_id=self.hardware_id,
                public_key_b64=base64.b64encode(
                    self.key.public_key().public_bytes(
                        Encoding.Raw, PublicFormat.Raw,
                    )
                ).decode(),
                pairing_id=str(uuid4()),
                authorized_by_user_id=1,
                registered_at=self.now,
                status="registered_awaiting_cloud_auth",
            ))
            db.add(RegisteredCollector(
                collector_id=collector_id_for_pi(self.hardware_id),
                name="Test Pi", customer_id=None,
                token_hash="unused", enabled=False,
            ))
            db.add(Device(
                device_id=self.device_id, source="discovered", online=False,
                status="pending_assignment", last_seen=self.now - timedelta(seconds=10),
                temperature_c=0, pressure_mpa=0, customer_id=42,
            ))
            db.add(PrinterDiscoveryLink(
                device_id=self.device_id,
                collector_id=collector_id_for_pi(self.hardware_id),
                manufacturer="Hitachi", serial_text="12345", protocol="modbus",
                first_discovered=self.now, last_reported=self.now,
            ))
            db.commit()

    def challenge(self, expired=False):
        cid = str(uuid4())
        nonce = base64.b64encode(bytes(range(32))).decode()
        with self.session() as db:
            db.add(PiCloudChallenge(
                challenge_id=cid, hardware_id=self.hardware_id,
                nonce_b64=nonce, state="pending",
                created_at=self.now,
                expires_at=datetime.now(timezone.utc) + timedelta(
                    seconds=-1 if expired else 60
                ),
            ))
            db.commit()
        return cid, nonce

    def payload(self, **overrides):
        base = dict(
            device_id=self.device_id, timestamp=self.now.isoformat(),
            status="printing", print_count=125,
            temperature_c=26.5, pressure_mpa=0.25,
            ink_level_percent=None, makeup_level_percent=None,
        )
        return dict(base, **overrides)

    def send(self, *, measurement=None, key=None, challenge=None, signed=None):
        cid, nonce = challenge or self.challenge()
        data = measurement or self.payload()
        normalized = pi_telemetry_api.PiMeasurement.model_validate(
            signed or data
        )
        signature = (key or self.key).sign(pi_telemetry_api.telemetry_message(
            cid, self.hardware_id, nonce, normalized,
        ))
        return self.client.post("/api/pi-telemetry/ingest", json={
            "hardware_id": self.hardware_id, "challenge_id": cid,
            "signature_b64": base64.b64encode(signature).decode(),
            "measurement": data,
        }), cid, nonce

    def test_authenticated_assigned_pi_stores_measurement(self):
        response, cid, _ = self.send()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertFalse(response.json()["controls_enabled"])
        with self.session() as db:
            rows = db.scalars(select(Measurement)).all()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].device_id, self.device_id)
            self.assertEqual(rows[0].print_count, 125)
            device = db.get(Device, self.device_id)
            self.assertTrue(device.online)
            self.assertEqual(device.customer_id, 42)
            self.assertEqual(db.get(PiCloudChallenge, cid).state, "telemetry_stored")

    def test_wrong_key_and_challenge_replay_rejected(self):
        challenge = self.challenge()
        response, _, _ = self.send(
            challenge=challenge, key=Ed25519PrivateKey.generate()
        )
        self.assertEqual(response.status_code, 403)
        response, _, _ = self.send(challenge=challenge)
        self.assertEqual(response.status_code, 409)
        with self.session() as db:
            self.assertEqual(db.query(Measurement).count(), 0)

    def test_signed_payload_tampering_rejected(self):
        response, _, _ = self.send(
            measurement=self.payload(print_count=999),
            signed=self.payload(print_count=125),
        )
        self.assertEqual(response.status_code, 403)

    def test_pi_cannot_write_another_printer(self):
        response, _, _ = self.send(
            measurement=self.payload(device_id="different-printer")
        )
        self.assertEqual(response.status_code, 403)

    def test_unassigned_printer_cannot_receive_telemetry(self):
        with self.session() as db:
            db.get(Device, self.device_id).customer_id = None
            db.commit()
        response, _, _ = self.send()
        self.assertEqual(response.status_code, 403)

    def test_stale_measurement_does_not_replace_newer_state(self):
        with self.session() as db:
            db.get(Device, self.device_id).last_seen = self.now + timedelta(seconds=1)
            db.commit()
        response, _, _ = self.send()
        self.assertEqual(response.status_code, 409)

    def test_expired_challenge_rejected(self):
        response, _, _ = self.send(challenge=self.challenge(expired=True))
        self.assertEqual(response.status_code, 410)

    def test_invalid_measurement_rejected(self):
        response = self.client.post("/api/pi-telemetry/ingest", json={
            "hardware_id": self.hardware_id,
            "challenge_id": str(uuid4()),
            "signature_b64": base64.b64encode(bytes(64)).decode(),
            "measurement": self.payload(pressure_mpa=-1),
        })
        self.assertEqual(response.status_code, 422)

    def test_future_timestamp_rejected(self):
        response, _, _ = self.send(measurement=self.payload(
            timestamp=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        ))
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
