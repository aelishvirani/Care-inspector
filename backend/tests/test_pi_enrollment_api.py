"""Isolated HTTP contract tests: pending Pi enrollment never authorizes access."""
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.auth import get_current_user
from backend.app import pi_enrollment_api
from backend.app.pi_pairing import PiPairingAttempt
from backend.app.pi_enrollment import PiEnrollmentRequest


class PiEnrollmentTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        PiPairingAttempt.__table__.create(self.engine)
        PiEnrollmentRequest.__table__.create(self.engine)
        self.session = sessionmaker(bind=self.engine, autoflush=False)
        self.patch = patch.object(pi_enrollment_api, "SessionLocal", self.session)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.addCleanup(self.engine.dispose)
        self.user = SimpleNamespace(id=101, role="TECHNICIAN")
        app = FastAPI()
        app.include_router(pi_enrollment_api.router)
        app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def seed_pair(self, status="proof_validated", hardware="pi-00000000abcdef12"):
        from uuid import uuid4
        pairing_id = str(uuid4())
        with self.session() as db:
            now = datetime.now(timezone.utc)
            db.add(PiPairingAttempt(
                pairing_id=pairing_id,
                actor_user_id=101,
                hardware_id=hardware,
                public_key_b64="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
                challenge_b64="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
                expires_at=now,
                created_at=now,
                status=status,
            ))
            db.commit()
        return pairing_id

    def request(self, pairing_id):
        return self.client.post(
            "/api/secure/management/pi-enrollment/requests",
            json={"pairing_id": pairing_id},
        )

    def test_verified_key_proof_creates_pending_only(self):
        pairing_id = self.seed_pair()
        r = self.request(pairing_id)
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(r.json()["status"], "pending_ownership_review")
        self.assertFalse(r.json()["trusted_device"])
        self.assertFalse(r.json()["cloud_credentials_issued"])
        with self.session() as db:
            row = db.query(PiEnrollmentRequest).one()
            self.assertEqual(row.status, "pending_ownership_review")

    def test_unverified_pairing_rejected(self):
        self.assertEqual(self.request(self.seed_pair(status="pending")).status_code, 409)

    def test_replayed_pairing_rejected(self):
        pairing = self.seed_pair()
        self.assertEqual(self.request(pairing).status_code, 201)
        self.assertEqual(self.request(pairing).status_code, 409)

    def test_duplicate_hardware_rejected(self):
        first = self.seed_pair()
        second = self.seed_pair()
        self.assertEqual(self.request(first).status_code, 201)
        self.assertEqual(self.request(second).status_code, 409)

    def test_customer_denied(self):
        self.user.role = "CUSTOMER"
        self.assertEqual(self.request(self.seed_pair()).status_code, 403)

    def test_unrelated_technician_cannot_submit(self):
        pairing = self.seed_pair()
        self.user.id = 202
        self.assertEqual(self.request(pairing).status_code, 404)


if __name__ == "__main__":
    unittest.main()
