"""Isolated HTTP tests for registered-Pi cloud key challenge verification."""
import base64
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app import pi_cloud_auth_api
from backend.app.pi_cloud_crypto import cloud_message
from backend.app.pi_cloud_challenges import PiCloudChallenge
from backend.app.pi_heartbeat import PiHeartbeat
from backend.app.pi_registered_devices import PiRegisteredDevice
from backend.app.pi_pairing import PiPairingAttempt
from backend.app.models import User


class CloudAuthApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        # Respect foreign-key dependencies in this isolated SQLite schema.
        # registered_devices -> pairing_attempts -> users.
        for model in (User, PiPairingAttempt, PiRegisteredDevice, PiCloudChallenge, PiHeartbeat):
            model.__table__.create(self.engine)
        self.session = sessionmaker(bind=self.engine, autoflush=False)
        self.patch = patch.object(pi_cloud_auth_api, "SessionLocal", self.session)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.addCleanup(self.engine.dispose)
        self.app = FastAPI()
        self.app.include_router(pi_cloud_auth_api.router)
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)
        self.key = Ed25519PrivateKey.generate()
        self.hardware_id = "pi-00000000abcdef12"
        self.register()

    def register(self):
        with self.session() as db:
            db.add(PiRegisteredDevice(
                hardware_id=self.hardware_id,
                public_key_b64=base64.b64encode(
                    self.key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
                ).decode("ascii"),
                pairing_id="de6458bb-b759-40f7-830e-b68fc137a7c1",
                authorized_by_user_id=101,
                status="registered_awaiting_cloud_auth",
                registered_at=datetime.now(timezone.utc),
            ))
            db.commit()

    def challenge(self):
        return self.client.post(
            "/api/pi-auth/challenge", json={"hardware_id": self.hardware_id}
        )

    def proof(self, challenge, key=None):
        signature = (key or self.key).sign(
            cloud_message(challenge["challenge_id"], self.hardware_id,
                          challenge["nonce_b64"])
        )
        return self.client.post("/api/pi-auth/prove", json={
            "hardware_id": self.hardware_id,
            "challenge_id": challenge["challenge_id"],
            "signature_b64": base64.b64encode(signature).decode("ascii"),
        })

    def test_valid_proof_and_no_cloud_session(self):
        challenge_response = self.challenge()
        self.assertEqual(challenge_response.status_code, 201)
        r = self.proof(challenge_response.json())
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.json()["authenticated"])
        self.assertFalse(r.json()["collector_access_granted"])
        self.assertFalse(r.json()["cloud_session_issued"])
        with self.session() as db:
            heartbeat = db.get(PiHeartbeat, self.hardware_id)
            self.assertIsNotNone(heartbeat)
            self.assertIsNotNone(heartbeat.last_authenticated_at)

    def test_replay_rejected(self):
        challenge = self.challenge().json()
        self.assertEqual(self.proof(challenge).status_code, 200)
        self.assertEqual(self.proof(challenge).status_code, 409)

    def test_wrong_key_rejected_and_consumes_challenge(self):
        challenge = self.challenge().json()
        self.assertEqual(
            self.proof(challenge, Ed25519PrivateKey.generate()).status_code, 403
        )
        self.assertEqual(self.proof(challenge).status_code, 409)
        with self.session() as db:
            self.assertIsNone(db.get(PiHeartbeat, self.hardware_id))

    def test_expired_challenge_rejected(self):
        challenge = self.challenge().json()
        with self.session() as db:
            row = db.get(PiCloudChallenge, challenge["challenge_id"])
            row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            db.commit()
        self.assertEqual(self.proof(challenge).status_code, 410)

    def test_unknown_pi_rejected(self):
        r = self.client.post("/api/pi-auth/challenge", json={
            "hardware_id": "pi-unknown0000000"
        })
        self.assertEqual(r.status_code, 404)

    def test_pending_challenge_limit(self):
        for _ in range(3):
            self.assertEqual(self.challenge().status_code, 201)
        self.assertEqual(self.challenge().status_code, 429)


if __name__ == "__main__":
    unittest.main()
