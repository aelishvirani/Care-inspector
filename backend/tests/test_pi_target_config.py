"""Staged Pi printer settings: validation, access control, optimistic versioning."""
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app import pi_target_config_api
from backend.app.models import User, AuditLog, Customer
from backend.app.pi_pairing import PiPairingAttempt
from backend.app.pi_registered_devices import PiRegisteredDevice
from backend.app.pi_target_config import PiTargetConfiguration


class PiTargetConfigTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        for model in (User, Customer, AuditLog, PiPairingAttempt,
                      PiRegisteredDevice, PiTargetConfiguration):
            model.__table__.create(self.engine)
        self.session = sessionmaker(bind=self.engine, autoflush=False)
        self.patch = patch.object(pi_target_config_api, "SessionLocal", self.session)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.addCleanup(self.engine.dispose)

        with self.session() as db:
            db.add(User(id=1, email="tech@example.org", password_hash="unused",
                        role="TECHNICIAN", active=True))
            db.add(User(id=2, email="customer@example.org", password_hash="unused",
                        role="CUSTOMER", active=True))
            db.add(PiPairingAttempt(
                pairing_id="11111111-1111-1111-1111-111111111111",
                hardware_id="pi-00000000abcdef12",
                actor_user_id=1,
                public_key_b64="A" * 44,
                challenge_b64="A" * 44,
                status="registered",
                created_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc),
            ))
            db.add(PiRegisteredDevice(
                hardware_id="pi-00000000abcdef12",
                public_key_b64="A" * 44,
                pairing_id="11111111-1111-1111-1111-111111111111",
                authorized_by_user_id=1,
                registered_at=datetime.now(timezone.utc),
                status="registered",
            ))
            db.commit()
        app = FastAPI()
        app.include_router(pi_target_config_api.router)
        app.dependency_overrides[pi_target_config_api.get_current_user] = lambda: self.user
        self.user = SimpleNamespace(id=1, email="tech@example.org", role="TECHNICIAN")
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.url = "/api/secure/management/pi-targets/pi-00000000abcdef12"
        self.printers = [{"host": "192.168.1.50", "port": 502,
                          "manufacturer": "Hitachi", "protocol": "modbus"}]

    def test_versioned_stage_and_read(self):
        first = self.client.put(self.url, json={
            "expected_version": 0, "printers": self.printers,
        })
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json()["version"], 1)
        self.assertFalse(first.json()["applied_to_pi"])
        saved = self.client.get(self.url)
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.json()["printers"][0]["host"], "192.168.1.50")
        second = self.client.put(self.url, json={
            "expected_version": 1, "printers": [],
        })
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(second.json()["version"], 2)

    def test_stale_update_rejected(self):
        self.assertEqual(self.client.put(self.url, json={
            "expected_version": 0, "printers": self.printers,
        }).status_code, 200)
        self.assertEqual(self.client.put(self.url, json={
            "expected_version": 0, "printers": [],
        }).status_code, 409)

    def test_bad_external_ip_rejected(self):
        payload = dict(self.printers[0], host="8.8.8.8")
        self.assertEqual(self.client.put(self.url, json={
            "expected_version": 0, "printers": [payload],
        }).status_code, 422)

    def test_unknown_printer_protocol_rejected(self):
        payload = dict(self.printers[0], protocol="tcp")
        self.assertEqual(self.client.put(self.url, json={
            "expected_version": 0, "printers": [payload],
        }).status_code, 422)

    def test_two_distinct_printers_rejected_for_one_pi(self):
        second = dict(self.printers[0], host="192.168.1.51")
        response = self.client.put(self.url, json={
            "expected_version": 0,
            "printers": [self.printers[0], second],
        })
        self.assertEqual(response.status_code, 422)
        with self.session() as db:
            self.assertIsNone(db.get(PiTargetConfiguration, "pi-00000000abcdef12"))

    def test_duplicate_endpoint_rejected(self):
        self.assertEqual(self.client.put(self.url, json={
            "expected_version": 0, "printers": self.printers * 2,
        }).status_code, 422)

    def test_customer_cannot_read_or_write(self):
        self.user.role = "CUSTOMER"
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.put(self.url, json={
            "expected_version": 0, "printers": self.printers,
        }).status_code, 403)

    def test_unregistered_pi_rejected(self):
        self.assertEqual(self.client.get(
            "/api/secure/management/pi-targets/pi-unknown123"
        ).status_code, 404)


if __name__ == "__main__":
    unittest.main()
