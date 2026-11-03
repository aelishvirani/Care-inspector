"""Test challenge messages, invalid signatures, and one-time proof primitives."""
import base64
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from backend.app.pi_pairing_crypto import (
    decode_b64,
    signed_message,
    verify_pi_proof,
)


class PiPairingCryptoTests(unittest.TestCase):
    def setUp(self):
        self.private = Ed25519PrivateKey.generate()
        self.pub = base64.b64encode(
            self.private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        ).decode("ascii")
        self.id = "f6970c9e-a76d-4b1e-81b4-40fb521c3c1d"
        self.hardware = "pi-00000000abcdef12"
        self.challenge = base64.b64encode(bytes(range(32))).decode("ascii")

    def test_valid_key_possession_proof(self):
        signature = base64.b64encode(
            self.private.sign(signed_message(self.id, self.hardware, self.challenge))
        ).decode("ascii")
        self.assertTrue(verify_pi_proof(
            self.pub, self.id, self.hardware, self.challenge, signature
        ))

    def test_different_challenge_fails(self):
        signature = base64.b64encode(
            self.private.sign(signed_message(self.id, self.hardware, self.challenge))
        ).decode("ascii")
        other = base64.b64encode(b"x" * 32).decode("ascii")
        self.assertFalse(verify_pi_proof(
            self.pub, self.id, self.hardware, other, signature
        ))

    def test_wrong_public_key_fails(self):
        signature = base64.b64encode(
            self.private.sign(signed_message(self.id, self.hardware, self.challenge))
        ).decode("ascii")
        other_key = Ed25519PrivateKey.generate().public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw
        )
        self.assertFalse(verify_pi_proof(
            base64.b64encode(other_key).decode("ascii"),
            self.id, self.hardware, self.challenge, signature
        ))

    def test_invalid_base64_or_length_rejected(self):
        with self.assertRaises(ValueError):
            decode_b64("not a valid base64!", 32)
        with self.assertRaises(ValueError):
            decode_b64(base64.b64encode(b"short").decode("ascii"), 32)


if __name__ == "__main__":
    unittest.main()
