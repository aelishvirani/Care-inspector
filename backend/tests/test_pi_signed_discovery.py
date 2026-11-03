"""End-to-end isolated signed inventory tests; no printer or cloud hardware."""
import base64
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app import pi_signed_discovery
from backend.app.collectors import RegisteredCollector
from backend.app.collectors_api import DiscoveryAnnouncement
from backend.app.models import User, Customer, Device
from backend.app.pi_pairing import PiPairingAttempt
from backend.app.pi_registered_devices import PiRegisteredDevice
from backend.app.pi_cloud_challenges import PiCloudChallenge
from backend.app.printer_discovery_links import PrinterDiscoveryLink


class SignedDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        for model in (
            User, Customer, Device, PiPairingAttempt, PiRegisteredDevice,
            PiCloudChallenge, RegisteredCollector, PrinterDiscoveryLink,
        ):
            model.__table__.create(self.engine)
        self.session = sessionmaker(bind=self.engine, autoflush=False)
        self.patch = patch.object(pi_signed_discovery, "SessionLocal", self.session)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.addCleanup(self.engine.dispose)
        app = FastAPI()
        app.include_router(pi_signed_discovery.router)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.key = Ed25519PrivateKey.generate()
        self.hardware_id = "pi-00000000abcdef12"
        self.announcement = {
            "mac_address": "dc:a6:32:12:34:56",
            "printers": [{
                "device_id": "hitachi-test-1001", "manufacturer": "Hitachi",
                "serial_number": "UX2-X10", "protocol": "modbus",
            }],
        }
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
                registered_at=datetime.now(timezone.utc),
                status="registered_awaiting_cloud_auth",
            ))
            db.commit()

    def challenge(self, expired=False):
        challenge_id = str(uuid4())
        nonce = base64.b64encode(bytes(range(32))).decode()
        now = datetime.now(timezone.utc)
        with self.session() as db:
            db.add(PiCloudChallenge(
                challenge_id=challenge_id, hardware_id=self.hardware_id,
                nonce_b64=nonce, state="pending", created_at=now,
                expires_at=now + timedelta(seconds=-1 if expired else 60),
            ))
            db.commit()
        return challenge_id, nonce

    def announce(self, challenge_id, nonce, *, announcement=None, signing_key=None):
        original = DiscoveryAnnouncement.model_validate(self.announcement)
        signature = (signing_key or self.key).sign(pi_signed_discovery.discovery_message(
            challenge_id, self.hardware_id, nonce, original,
        ))
        return self.client.post("/api/pi-discovery/announce", json={
            "hardware_id": self.hardware_id,
            "challenge_id": challenge_id,
            "signature_b64": base64.b64encode(signature).decode(),
            "announcement": announcement or self.announcement,
        })

    def test_signed_discovery_adds_only_unassigned_printer(self):
        challenge_id, nonce = self.challenge()
        response = self.announce(challenge_id, nonce)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["authenticated_pi"])
        self.assertFalse(response.json()["controls_enabled"])
        with self.session() as db:
            device = db.get(Device, "hitachi-test-1001")
            self.assertIsNone(device.customer_id)
            self.assertFalse(device.online)
            self.assertEqual(device.status, "pending_assignment")
            collector = db.get(RegisteredCollector, response.json()["collector_id"])
            self.assertFalse(collector.enabled)
            self.assertEqual(
                db.get(PrinterDiscoveryLink, device.device_id).collector_id,
                collector.collector_id,
            )

    def test_tampered_payload_fails(self):
        cid, nonce = self.challenge()
        tampered = dict(self.announcement)
        tampered["printers"] = [dict(self.announcement["printers"][0], device_id="fake-999")]
        response = self.announce(cid, nonce, announcement=tampered)
        self.assertEqual(response.status_code, 403)
        with self.session() as db:
            self.assertIsNone(db.get(Device, "fake-999"))

    def test_wrong_key_and_replay_rejected(self):
        cid, nonce = self.challenge()
        self.assertEqual(
            self.announce(cid, nonce, signing_key=Ed25519PrivateKey.generate()).status_code,
            403,
        )
        self.assertEqual(self.announce(cid, nonce).status_code, 409)

    def test_duplicate_announcement_preserves_customer(self):
        cid, nonce = self.challenge()
        self.assertEqual(self.announce(cid, nonce).status_code, 200)
        with self.session() as db:
            db.get(Device, "hitachi-test-1001").customer_id = 42
            db.commit()
        cid, nonce = self.challenge()
        result = self.announce(cid, nonce)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()["printers"][0]["status"], "known")
        with self.session() as db:
            self.assertEqual(db.get(Device, "hitachi-test-1001").customer_id, 42)

    def test_expired_challenge_rejected(self):
        cid, nonce = self.challenge(expired=True)
        self.assertEqual(self.announce(cid, nonce).status_code, 410)


    def test_one_pi_rejects_two_printers_without_creating_inventory(self):
        cid, nonce = self.challenge()
        second = dict(self.announcement["printers"][0], device_id="hitachi-test-1002")
        payload = dict(self.announcement, printers=[
            self.announcement["printers"][0], second,
        ])
        original = DiscoveryAnnouncement.model_validate(payload)
        signature = self.key.sign(pi_signed_discovery.discovery_message(
            cid, self.hardware_id, nonce, original,
        ))
        response = self.client.post("/api/pi-discovery/announce", json={
            "hardware_id": self.hardware_id, "challenge_id": cid,
            "signature_b64": base64.b64encode(signature).decode(),
            "announcement": payload,
        })
        self.assertEqual(response.status_code, 409, response.text)
        with self.session() as db:
            self.assertEqual(db.query(PrinterDiscoveryLink).count(), 0)
            self.assertEqual(db.query(RegisteredCollector).count(), 0)
            self.assertEqual(db.get(PiCloudChallenge, cid).state, "rejected")

    def test_one_pi_cannot_silently_replace_existing_printer(self):
        cid, nonce = self.challenge()
        self.assertEqual(self.announce(cid, nonce).status_code, 200)
        cid, nonce = self.challenge()
        payload = dict(self.announcement, printers=[
            dict(self.announcement["printers"][0], device_id="hitachi-test-1002")
        ])
        original = DiscoveryAnnouncement.model_validate(payload)
        signature = self.key.sign(pi_signed_discovery.discovery_message(
            cid, self.hardware_id, nonce, original,
        ))
        response = self.client.post("/api/pi-discovery/announce", json={
            "hardware_id": self.hardware_id, "challenge_id": cid,
            "signature_b64": base64.b64encode(signature).decode(),
            "announcement": payload,
        })
        self.assertEqual(response.status_code, 409, response.text)
        with self.session() as db:
            self.assertIsNotNone(db.get(Device, "hitachi-test-1001"))
            self.assertIsNone(db.get(Device, "hitachi-test-1002"))
            self.assertEqual(db.query(PrinterDiscoveryLink).count(), 1)


if __name__ == "__main__":
    unittest.main()
