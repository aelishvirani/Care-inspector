"""Pi and backend canonical signature parity without network or hardware."""
import base64
import unittest
from datetime import datetime, timezone
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.app.pi_telemetry_api import PiMeasurement, telemetry_message as server_message
from collector.pi_telemetry_client import (
    normalize_measurement, send_measurement,
    telemetry_message as client_message,
)


class PiTelemetryClientTests(unittest.TestCase):
    def setUp(self):
        self.key = Ed25519PrivateKey.generate()
        self.hardware = "pi-00000000abcdef12"
        self.cid = str(uuid4())
        self.nonce = base64.b64encode(bytes(range(32))).decode()
        self.reading = {
            "device_id": "hitachi-test-1001",
            "timestamp": datetime(2026, 11, 4, 10, 0, tzinfo=timezone.utc).isoformat(),
            "status": "printing", "print_count": 122,
            "temperature_c": 26.5, "pressure_mpa": 0.251,
            "ink_level_percent": None, "makeup_level_percent": None,
            "source": "hitachi_modbus", "online": True,
        }

    def test_canonical_contract_matches_backend(self):
        normalized = normalize_measurement(self.reading)
        self.assertEqual(
            client_message(self.cid, self.hardware, self.nonce, normalized),
            server_message(
                self.cid, self.hardware, self.nonce,
                PiMeasurement.model_validate(normalized),
            ),
        )

    def test_signed_request_uses_challenge_and_valid_signature(self):
        calls = []
        def post(url, path, data):
            calls.append(path)
            if path.endswith("/challenge"):
                return {"challenge_id": self.cid, "nonce_b64": self.nonce}
            expected = server_message(
                data["challenge_id"], data["hardware_id"], self.nonce,
                PiMeasurement.model_validate(data["measurement"]),
            )
            self.key.public_key().verify(
                base64.b64decode(data["signature_b64"]), expected,
            )
            self.assertNotIn("source", data["measurement"])
            self.assertNotIn("online", data["measurement"])
            return {"status": "stored"}
        result = send_measurement(
            "https://example.invalid", self.hardware, self.key, self.reading,
            post=post,
        )
        self.assertEqual(result["status"], "stored")
        self.assertEqual(calls, [
            "/api/pi-auth/challenge", "/api/pi-telemetry/ingest",
        ])

    def test_invalid_reading_rejected_before_network(self):
        for update in (
            {"pressure_mpa": float("nan")},
            {"timestamp": "not-a-date"},
            {"device_id": ""},
            {"ink_level_percent": 101},
        ):
            with self.subTest(update=update), self.assertRaises(ValueError):
                send_measurement(
                    "https://example.invalid", self.hardware, self.key,
                    dict(self.reading, **update),
                    post=lambda *args: self.fail("No network calls expected"),
                )


if __name__ == "__main__":
    unittest.main()
