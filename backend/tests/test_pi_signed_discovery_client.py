"""Test client-server signed inventory contract without network or hardware."""
import base64
import unittest
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from backend.app.collectors_api import DiscoveryAnnouncement
from backend.app.pi_signed_discovery import discovery_message as server_message
from collector.pi_signed_discovery_client import (
    announce_printers, discovery_message as client_message,
    normalize_inventory,
)


class SignedDiscoveryClientTests(unittest.TestCase):
    def setUp(self):
        self.hardware = "pi-00000000abcdef12"
        self.key = Ed25519PrivateKey.generate()
        self.challenge_id = str(uuid4())
        self.nonce = base64.b64encode(bytes(range(32))).decode()
        self.mac = "dc:a6:32:12:34:56"
        self.printers = [
            {"device_id": "hitachi-ux2-123", "manufacturer": "Hitachi",
             "serial_number": "UX2-X10", "protocol": "modbus"}
        ]

    def test_client_server_canonical_message_matches(self):
        inventory = normalize_inventory(self.mac, self.printers)
        expected = server_message(
            self.challenge_id, self.hardware, self.nonce,
            DiscoveryAnnouncement.model_validate(inventory),
        )
        actual = client_message(
            self.challenge_id, self.hardware, self.nonce, inventory,
        )
        self.assertEqual(actual, expected)

    def test_signed_announcement_contract(self):
        calls = []
        def post(url, path, payload):
            calls.append((path, payload))
            if path.endswith("challenge"):
                return {"challenge_id": self.challenge_id, "nonce_b64": self.nonce}
            message = server_message(
                payload["challenge_id"], payload["hardware_id"], self.nonce,
                DiscoveryAnnouncement.model_validate(payload["announcement"]),
            )
            self.key.public_key().verify(
                base64.b64decode(payload["signature_b64"]), message,
            )
            return {"authenticated_pi": True, "printers": [{"status": "unassigned"}]}
        result = announce_printers(
            "https://care.example.org", self.hardware, self.key,
            self.mac, self.printers, post=post,
        )
        self.assertTrue(result["authenticated_pi"])
        self.assertEqual([p for p, _ in calls],
                         ["/api/pi-auth/challenge", "/api/pi-discovery/announce"])

    def test_multiple_printers_rejected_without_network(self):
        second = dict(self.printers[0], device_id="hitachi-ux2-124")
        with self.assertRaises(ValueError):
            announce_printers(
                "https://care.example.org", self.hardware, self.key,
                self.mac, self.printers + [second],
                post=lambda *args: self.fail("No cloud calls expected"),
            )

    def test_no_extra_fields_accepted(self):
        with self.assertRaises(ValueError):
            normalize_inventory(self.mac, [{"device_id": "foo", "password": "secret"}])


if __name__ == "__main__":
    unittest.main()
