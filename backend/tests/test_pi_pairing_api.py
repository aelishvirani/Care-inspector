"""End-to-end HTTP tests for Pi key-proof API with an isolated SQLite database.

No production accounts, JWTs, collectors or persistent Care-Inspector data.
"""
import base64
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.auth import get_current_user
from backend.app import pi_pairing_api
from backend.app.pi_pairing import PiPairingAttempt
from backend.app.pi_pairing_crypto import signed_message


class PiPairingApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        PiPairingAttempt.__table__.create(self.engine)
        session_factory = sessionmaker(bind=self.engine, autoflush=False)
        self.db_patch = patch.object(pi_pairing_api, "SessionLocal", session_factory)
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        self.addCleanup(self.engine.dispose)

        app = FastAPI()
        app.include_router(pi_pairing_api.router)
        self.user = SimpleNamespace(id=101, role="TECHNICIAN")
        app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

        self.private_key = Ed25519PrivateKey.generate()
        self.public_key_b64 = base64.b64encode(
            self.private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        ).decode("ascii")
        self.hardware_id = "pi-00000000abcdef12"

    def start(self):
        return self.client.post(
            "/api/secure/management/pi-pairing/start",
            json={"hardware_id": self.hardware_id, "public_key_b64": self.public_key_b64},
        )

    def signature_for(self, pair):
        message = signed_message(
            pair["pairing_id"], self.hardware_id, pair["challenge_b64"]
        )
        return base64.b64encode(self.private_key.sign(message)).decode("ascii")

    def test_valid_proof_is_not_enrollment_and_replay_rejected(self):
        response = self.start()
        self.assertEqual(response.status_code, 201, response.text)
        pair = response.json()
        self.assertFalse(pair["enrolled"])
        url = f"/api/secure/management/pi-pairing/{pair['pairing_id']}/verify"
        proof = {"signature_b64": self.signature_for(pair)}
        verified = self.client.post(url, json=proof)
        self.assertEqual(verified.status_code, 200, verified.text)
        self.assertEqual(verified.json()["status"], "key_possession_confirmed")
        self.assertFalse(verified.json()["trusted_device"])
        self.assertFalse(verified.json()["enrolled"])
        self.assertEqual(self.client.post(url, json=proof).status_code, 409)

    def test_invalid_proof_consumes_challenge(self):
        pair = self.start().json()
        url = f"/api/secure/management/pi-pairing/{pair['pairing_id']}/verify"
        other_key = Ed25519PrivateKey.generate()
        wrong_sig = base64.b64encode(other_key.sign(signed_message(
            pair["pairing_id"], self.hardware_id, pair["challenge_b64"]
        ))).decode("ascii")
        self.assertEqual(
            self.client.post(url, json={"signature_b64": wrong_sig}).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(url, json={"signature_b64": self.signature_for(pair)}).status_code,
            409,
        )

    def test_expired_challenge_rejected(self):
        from datetime import datetime, timedelta, timezone
        pair = self.start().json()
        with pi_pairing_api.SessionLocal() as db:
            row = db.get(PiPairingAttempt, pair["pairing_id"])
            row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            db.commit()
        response = self.client.post(
            f"/api/secure/management/pi-pairing/{pair['pairing_id']}/verify",
            json={"signature_b64": self.signature_for(pair)},
        )
        self.assertEqual(response.status_code, 410, response.text)

    def test_customer_cannot_start_pairing(self):
        self.user.role = "CUSTOMER"
        response = self.start()
        self.assertEqual(response.status_code, 403)

    def test_another_technician_cannot_verify(self):
        pair = self.start().json()
        self.user.id = 202
        response = self.client.post(
            f"/api/secure/management/pi-pairing/{pair['pairing_id']}/verify",
            json={"signature_b64": self.signature_for(pair)},
        )
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
