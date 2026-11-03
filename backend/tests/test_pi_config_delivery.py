"""Isolated signed configuration delivery tests; no physical Pi, printer or network."""
import base64
import json
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

from backend.app import pi_config_delivery
from backend.app.models import User
from backend.app.pi_pairing import PiPairingAttempt
from backend.app.pi_registered_devices import PiRegisteredDevice
from backend.app.pi_cloud_challenges import PiCloudChallenge
from backend.app.pi_target_config import PiTargetConfiguration
from collector.pi_config_client import fetch_message, fetch_targets


class PiConfigDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://",
            connect_args={"check_same_thread": False}, poolclass=StaticPool)
        for cls in (User, PiPairingAttempt, PiRegisteredDevice,
                    PiCloudChallenge, PiTargetConfiguration):
            cls.__table__.create(self.engine)
        self.sessions = sessionmaker(bind=self.engine, autoflush=False)
        self.patcher = patch.object(pi_config_delivery, "SessionLocal", self.sessions)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.addCleanup(self.engine.dispose)
        app = FastAPI()
        app.include_router(pi_config_delivery.router)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.hardware_id = "pi-00000000abcdef12"
        self.key = Ed25519PrivateKey.generate()
        now = datetime.now(timezone.utc)
        with self.sessions() as db:
            db.add(User(id=1, email="tech@example.invalid", password_hash="unused",
                        role="TECHNICIAN", active=True))
            db.add(PiPairingAttempt(
                pairing_id="11111111-1111-1111-1111-111111111111",
                hardware_id=self.hardware_id, actor_user_id=1,
                public_key_b64="A" * 44, challenge_b64="A" * 44,
                status="registered", created_at=now,
                expires_at=now + timedelta(minutes=1),
            ))
            db.add(PiRegisteredDevice(
                hardware_id=self.hardware_id,
                public_key_b64=base64.b64encode(self.key.public_key().public_bytes(
                    Encoding.Raw, PublicFormat.Raw)).decode("ascii"),
                pairing_id="11111111-1111-1111-1111-111111111111",
                authorized_by_user_id=1, status="registered",
                registered_at=now,
            ))
            db.add(PiTargetConfiguration(
                hardware_id=self.hardware_id, version=4,
                targets_json=json.dumps([{
                    "host": "192.168.1.50", "port": 502,
                    "protocol": "modbus", "manufacturer": "Hitachi",
                    "device_id": "",
                }]),
                updated_by_user_id=1, updated_at=now,
            ))
            db.commit()

    def challenge(self, expired=False):
        now = datetime.now(timezone.utc)
        cid = str(uuid4())
        nonce = base64.b64encode(bytes(range(32))).decode("ascii")
        with self.sessions() as db:
            db.add(PiCloudChallenge(
                challenge_id=cid, hardware_id=self.hardware_id,
                nonce_b64=nonce, state="pending", created_at=now,
                expires_at=now + timedelta(seconds=-1 if expired else 60),
            ))
            db.commit()
        return cid, nonce

    def request(self, cid, nonce, signing_key=None):
        signature = (signing_key or self.key).sign(
            fetch_message(cid, self.hardware_id, nonce))
        return self.client.post("/api/pi-config/fetch", json={
            "hardware_id": self.hardware_id, "challenge_id": cid,
            "signature_b64": base64.b64encode(signature).decode("ascii"),
        })

    def test_registered_pi_fetches_only_staged_targets(self):
        cid, nonce = self.challenge()
        resp = self.request(cid, nonce)
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["version"], 4)
        self.assertEqual(resp.json()["printers"][0]["host"], "192.168.1.50")
        self.assertFalse(resp.json()["configuration_applied"])

    def test_invalid_signature_rejected_and_consumed(self):
        cid, nonce = self.challenge()
        self.assertEqual(self.request(cid, nonce, Ed25519PrivateKey.generate()).status_code, 403)
        self.assertEqual(self.request(cid, nonce).status_code, 409)

    def test_expired_challenge_rejected(self):
        cid, nonce = self.challenge(expired=True)
        self.assertEqual(self.request(cid, nonce).status_code, 410)

    def test_replay_after_valid_fetch_rejected(self):
        cid, nonce = self.challenge()
        self.assertEqual(self.request(cid, nonce).status_code, 200)
        self.assertEqual(self.request(cid, nonce).status_code, 409)

    def test_discovery_signature_cannot_fetch_configuration(self):
        from backend.app.collectors_api import DiscoveryAnnouncement
        from backend.app.pi_signed_discovery import discovery_message
        cid, nonce = self.challenge()
        signature = self.key.sign(discovery_message(
            cid, self.hardware_id, nonce,
            DiscoveryAnnouncement(mac_address="dc:a6:32:12:34:56", printers=[]),
        ))
        response = self.client.post("/api/pi-config/fetch", json={
            "hardware_id": self.hardware_id, "challenge_id": cid,
            "signature_b64": base64.b64encode(signature).decode("ascii"),
        })
        self.assertEqual(response.status_code, 403)

    def test_pi_client_signing_parity(self):
        cid, nonce = self.challenge()
        self.assertEqual(fetch_message(cid, self.hardware_id, nonce),
            pi_config_delivery.fetch_message(cid, self.hardware_id, nonce))

    def test_pi_client_uses_challenge_then_fetch(self):
        calls = []
        cid, nonce = self.challenge()
        def post(url, path, payload):
            calls.append(path)
            if path == "/api/pi-auth/challenge":
                return {"challenge_id": cid, "nonce_b64": nonce}
            resp = self.client.post(path, json=payload)
            self.assertEqual(resp.status_code, 200, resp.text)
            return resp.json()
        response = fetch_targets("https://care.example.invalid",
                                 self.hardware_id, self.key, post=post)
        self.assertEqual(response["version"], 4)
        self.assertEqual(calls, ["/api/pi-auth/challenge", "/api/pi-config/fetch"])


if __name__ == "__main__":
    unittest.main()
