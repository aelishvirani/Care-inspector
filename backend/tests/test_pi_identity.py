import json
import unittest

from collector.pi_identity import identity_payload


class PiIdentityTests(unittest.TestCase):
    def test_valid_identity(self):
        data = identity_payload(
            hardware_id="pi-00000000abcdef12",
            hostname="raspberrypi",
            model="Raspberry Pi 4 Model B",
            mac_address="dc:a6:32:12:34:56",
        )
        identity = json.loads(data)
        self.assertEqual(identity["model"], "Raspberry Pi 4 Model B")
        self.assertEqual(identity["hardware_id"], "pi-00000000abcdef12")
        self.assertLessEqual(len(data), 512)

    def test_missing_identity_rejected(self):
        with self.assertRaises(ValueError):
            identity_payload("", "raspberrypi", "Raspberry Pi 4")

    def test_bad_mac_rejected(self):
        with self.assertRaises(ValueError):
            identity_payload("pi-00000000abcdef12", "raspberrypi", "Raspberry Pi 4", "invalid")

    def test_overlong_payload_rejected(self):
        with self.assertRaises(ValueError):
            identity_payload(
                "pi-" + "a" * 125,
                "h" * 128,
                "Raspberry Pi " + "x" * 116,
                "dc:a6:32:12:34:56",
            )


if __name__ == "__main__":
    unittest.main()
