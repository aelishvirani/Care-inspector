"""Mac-safe tests for the Pi's key persistence and Bluetooth proof data."""
import base64
import json
import tempfile
import unittest
from pathlib import Path

from backend.app.pi_pairing_crypto import verify_pi_proof
from collector.pi_pairing_agent import (
    PairingSigner, load_or_create_private_key, public_key_b64,
)


class PiPairingAgentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.keypath = Path(self.tmp.name) / "identity.key"
        self.hardware_id = "pi-00000000abcdef12"
        self.pairing_id = "f6970c9e-a76d-4b1e-81b4-40fb521c3c1d"
        self.challenge = base64.b64encode(bytes(range(32))).decode("ascii")

    def test_persistent_key(self):
        one = load_or_create_private_key(self.keypath)
        two = load_or_create_private_key(self.keypath)
        self.assertEqual(public_key_b64(one), public_key_b64(two))
        self.assertEqual(self.keypath.stat().st_mode & 0o077, 0)

    def test_ble_signature_verified_by_cloud_crypto(self):
        key = load_or_create_private_key(self.keypath)
        signer = PairingSigner(key, self.hardware_id)
        signer.accept_challenge(json.dumps({
            "pairing_id": self.pairing_id,
            "hardware_id": self.hardware_id,
            "challenge_b64": self.challenge,
        }).encode("utf-8"))
        signature = signer.read_proof().decode("ascii")
        self.assertTrue(verify_pi_proof(
            public_key_b64(key), self.pairing_id, self.hardware_id,
            self.challenge, signature,
        ))
        self.assertEqual(signer.read_proof(10), signature.encode("ascii")[10:])

    def test_other_hardware_id_rejected(self):
        signer = PairingSigner(load_or_create_private_key(self.keypath), self.hardware_id)
        with self.assertRaises(ValueError):
            signer.accept_challenge(json.dumps({
                "pairing_id": self.pairing_id,
                "hardware_id": "pi-00000000deadbeef",
                "challenge_b64": self.challenge,
            }).encode())

    def test_no_proof_without_challenge(self):
        signer = PairingSigner(load_or_create_private_key(self.keypath), self.hardware_id)
        with self.assertRaises(ValueError):
            signer.read_proof()


if __name__ == "__main__":
    unittest.main()
