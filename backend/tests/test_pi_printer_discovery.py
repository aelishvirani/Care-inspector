"""Hitachi Pi discovery runner tests; no network, Raspberry Pi, or Modbus device."""
import json
import tempfile
import unittest
from pathlib import Path

from collector.pi_printer_discovery import (load_targets, parse_targets, fetch_remote_targets, discover_configured_hitachi)
from collector.printer_detection import PrinterTarget


class PiPrinterDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.target = {
            "host": "127.0.0.1", "port": 1502,
            "protocol": "modbus", "manufacturer": "Hitachi",
        }

    def load(self, data):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "printers.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            return load_targets(path)

    def test_valid_configured_hitachi(self):
        targets = self.load({"printers": [self.target]})
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0].port, 1502)

    def test_two_distinct_targets_rejected_for_one_pi(self):
        second = dict(self.target, host="127.0.0.2")
        with self.assertRaises(ValueError):
            self.load({"printers": [self.target, second]})

    def test_public_addresses_not_probed(self):
        with self.assertRaises(ValueError):
            self.load({"printers": [dict(self.target, host="8.8.8.8")]})

    def test_unknown_vendor_or_protocol_rejected(self):
        with self.assertRaises(ValueError):
            self.load({"printers": [dict(self.target, manufacturer="Domino")]})
        with self.assertRaises(ValueError):
            self.load({"printers": [dict(self.target, protocol="tcp")]})

    def test_invalid_configuration_rejected(self):
        with self.assertRaises(ValueError):
            self.load({"printers": [dict(self.target, port="502")]})
        with self.assertRaises(ValueError):
            self.load({"printers": [dict(self.target, password="secret")]})
        with self.assertRaises(ValueError):
            self.load({"targets": [self.target]})

    def test_identity_read_then_signed_announcement_bridge(self):
        observed = []
        def fake_probe(target):
            observed.append(("probe", target.host))
            return {"model_name": "UX2", "serial_number": "123456"}
        def fake_announce(url, printers):
            observed.append(("announce", url, printers))
            return {"printers": [{"status": "unassigned"}]}
        result = discover_configured_hitachi(
            "https://care.example.org",
            [PrinterTarget(**self.target)],
            probe=fake_probe, announce=fake_announce,
        )
        self.assertEqual(result["printers"][0]["status"], "unassigned")
        self.assertEqual(observed[0][0], "probe")
        self.assertEqual(observed[1][0], "announce")
        self.assertEqual(observed[1][2][0]["serial_number"], "123456")

    def test_no_identity_skips_announcement(self):
        result = discover_configured_hitachi(
            "https://care.example.org", [PrinterTarget(**self.target)],
            probe=lambda target: None,
            announce=lambda *args: self.fail("No printer should be announced"),
        )
        self.assertTrue(result["announcement_skipped"])


    def test_remote_configuration_opt_in_parses_valid_targets(self):
        remote = {"version": 2, "configuration_applied": False,
                  "printers": [self.target]}
        result = fetch_remote_targets(
            "https://care.example.org", fetch=lambda url: remote
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].host, "127.0.0.1")

    def test_remote_configuration_rejects_invalid_target(self):
        remote = {"version": 1, "configuration_applied": False,
                  "printers": [dict(self.target, host="8.8.8.8")]}
        with self.assertRaises(ValueError):
            fetch_remote_targets(
                "https://care.example.org", fetch=lambda url: remote
            )

    def test_remote_configuration_rejects_missing_targets(self):
        with self.assertRaises(ValueError):
            fetch_remote_targets(
                "https://care.example.org",
                fetch=lambda url: {"version": 1, "configuration_applied": False},
            )

    def test_remote_configuration_rejects_bad_version(self):
        with self.assertRaises(ValueError):
            fetch_remote_targets(
                "https://care.example.org",
                fetch=lambda url: {"version": True,
                                   "configuration_applied": False, "printers": []},
            )

    def test_local_configuration_still_parses(self):
        self.assertEqual(len(parse_targets({"printers": [self.target]})), 1)


if __name__ == "__main__":
    unittest.main()
