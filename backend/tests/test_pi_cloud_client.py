"""Client/server crypto contract tests without Pi hardware, network, or database."""
import base64
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.app.pi_cloud_crypto import verify_cloud_signature
from collector.pi_cloud_auth_client import (
    authenticate_pi, cloud_message, post_json, authenticate_from_pi,
)


class PiCloudClientTests(unittest.TestCase):
    def setUp(self):
        self.hardware_id = "pi-00000000abcdef12"
        self.key = Ed25519PrivateKey.generate()
        self.challenge_id = "4c0a0fc3-4a79-4f48-afd1-f575019a8f6b"
        self.nonce = base64.b64encode(bytes(range(32))).decode("ascii")
        self.calls = []

    def post(self, path, data):
        self.calls.append((path, data))
        if path.endswith("/challenge"):
            return {"challenge_id": self.challenge_id, "nonce_b64": self.nonce}
        self.assertTrue(verify_cloud_signature(
            base64.b64encode(
                self.key.public_key().public_bytes_raw()
            ).decode("ascii"),
            self.challenge_id, self.hardware_id, self.nonce,
            data["signature_b64"],
        ))
        return {"hardware_id": self.hardware_id, "authenticated": True,
                "cloud_session_issued": False, "collector_access_granted": False}

    def test_client_signs_correct_cloud_challenge(self):
        result = authenticate_pi(self.hardware_id, self.post, self.key)
        self.assertTrue(result["authenticated"])
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.calls[0][0], "/api/pi-auth/challenge")
        self.assertEqual(self.calls[1][0], "/api/pi-auth/prove")

    def test_wrong_server_identity_rejected(self):
        def wrong(path, data):
            if path.endswith("challenge"):
                return {"challenge_id": self.challenge_id, "nonce_b64": self.nonce}
            return {"hardware_id": "pi-other123", "authenticated": True}
        with self.assertRaises(PermissionError):
            authenticate_pi(self.hardware_id, wrong, self.key)

    def test_invalid_nonce_rejected_before_proof(self):
        def invalid(path, data):
            return {"challenge_id": self.challenge_id, "nonce_b64": "invalid"}
        with self.assertRaises(ValueError):
            authenticate_pi(self.hardware_id, invalid, self.key)

    def test_non_local_http_rejected(self):
        with self.assertRaises(ValueError):
            post_json("http://example.com", "/api/pi-auth/challenge", {})

    def test_existing_key_required(self):
        from pathlib import Path
        with self.assertRaises(FileNotFoundError):
            authenticate_from_pi("http://127.0.0.1:8000", Path("/not/a/real/pi-key"))


if __name__ == "__main__":
    unittest.main()
