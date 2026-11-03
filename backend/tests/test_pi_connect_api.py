"""Isolated Pi Connect endpoint tests, no real printer/collector credential issued."""
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.auth import get_current_user
from backend.app import pi_connect_api
from backend.app.models import AuditLog
from backend.app.pi_pairing import PiPairingAttempt
from backend.app.pi_registered_devices import PiRegisteredDevice


class PiConnectApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        for model in (PiPairingAttempt, PiRegisteredDevice, AuditLog):
            model.__table__.create(self.engine)
        self.session = sessionmaker(bind=self.engine, autoflush=False)
        self.patch = patch.object(pi_connect_api, "SessionLocal", self.session)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.addCleanup(self.engine.dispose)
        self.user = SimpleNamespace(
            id=101, role="TECHNICIAN", email="tech@example.invalid",
        )
        app = FastAPI()
        app.include_router(pi_connect_api.router)
        app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def pair(self, status="proof_validated", expired=False, hardware="pi-00000000abcdef12"):
        from uuid import uuid4
        pairing_id = str(uuid4())
        now = datetime.now(timezone.utc)
        with self.session() as db:
            db.add(PiPairingAttempt(
                pairing_id=pairing_id, actor_user_id=101,
                hardware_id=hardware,
                public_key_b64="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
                challenge_b64="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
                created_at=now,
                expires_at=now + timedelta(seconds=-10 if expired else 120),
                status=status,
            ))
            db.commit()
        return pairing_id

    def connect(self, pairing_id, approve=True):
        return self.client.post(
            "/api/secure/management/pi-connect",
            json={"pairing_id": pairing_id, "authorize_device": approve},
        )

    def test_explicit_connection_registers_key_not_cloud(self):
        response = self.connect(self.pair())
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["status"], "registered_awaiting_cloud_auth")
        self.assertFalse(response.json()["cloud_connected"])
        with self.session() as db:
            self.assertEqual(db.query(PiRegisteredDevice).count(), 1)
            self.assertEqual(db.query(AuditLog).count(), 1)

    def test_unverified_device_is_rejected(self):
        self.assertEqual(self.connect(self.pair(status="pending")).status_code, 409)

    def test_expired_proof_is_rejected(self):
        self.assertEqual(self.connect(self.pair(expired=True)).status_code, 410)

    def test_explicit_approval_required(self):
        self.assertEqual(self.connect(self.pair(), approve=False).status_code, 400)

    def test_repeat_connection_rejected(self):
        pair = self.pair()
        self.assertEqual(self.connect(pair).status_code, 201)
        self.assertEqual(self.connect(pair).status_code, 409)

    def test_customer_rejected(self):
        self.user.role = "CUSTOMER"
        self.assertEqual(self.connect(self.pair()).status_code, 403)

    def test_different_technician_rejected(self):
        pair = self.pair()
        self.user.id = 202
        self.assertEqual(self.connect(pair).status_code, 404)


if __name__ == "__main__":
    unittest.main()
