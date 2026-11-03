"""Configured printer detection tests, with no hardware or network."""
import unittest

from collector.printer_detection import (
    PrinterTarget, PrinterProbeError, detect_configured_printers,
    detect_and_announce,
)


class PrinterDetectionTests(unittest.TestCase):
    def setUp(self):
        self.target = PrinterTarget(
            host="127.0.0.1", port=1502, protocol="modbus",
            manufacturer="Hitachi", model_name="UX2",
        )
        self.probes = {"modbus": lambda target: {
            "serial_number": "UX2-12345", "model_name": "UX2"
        }}

    def test_read_only_probe_produces_signed_discovery_schema(self):
        devices = detect_configured_printers([self.target], self.probes)
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0]["manufacturer"], "Hitachi")
        self.assertEqual(devices[0]["serial_number"], "UX2-12345")
        self.assertEqual(devices[0]["protocol"], "modbus")
        self.assertNotIn("host", devices[0])

    def test_stable_id_independent_of_changed_ip_for_known_serial(self):
        one = detect_configured_printers([self.target], self.probes)
        second = PrinterTarget(host="192.168.1.42", port=502, protocol="modbus",
                               manufacturer="Hitachi")
        two = detect_configured_printers([second], self.probes)
        self.assertEqual(one[0]["device_id"], two[0]["device_id"])

    def test_no_response_does_not_create_inventory(self):
        self.assertEqual(
            detect_configured_printers([self.target], {"modbus": lambda t: None}), []
        )

    def test_unknown_protocol_rejected(self):
        with self.assertRaises(PrinterProbeError):
            detect_configured_printers([self.target], {})

    def test_public_address_rejected(self):
        target = PrinterTarget(host="8.8.8.8", port=502, protocol="modbus",
                               manufacturer="Hitachi")
        with self.assertRaises(ValueError):
            detect_configured_printers([target], self.probes)

    def test_duplicate_serial_rejected(self):
        with self.assertRaises(PrinterProbeError):
            detect_configured_printers([self.target, self.target], self.probes)

    def test_detect_then_announce_only_confirmed_printers(self):
        sent = []
        def announce(url, printers):
            sent.append((url, printers))
            return {"authenticated_pi": True, "printers": [{"status": "unassigned"}]}

        result = detect_and_announce(
            "https://example.invalid", [self.target], self.probes,
            announce=announce,
        )
        self.assertTrue(result["authenticated_pi"])
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0][1][0]["serial_number"], "UX2-12345")

    def test_empty_discovery_is_not_reported_as_removal(self):
        result = detect_and_announce(
            "https://example.invalid", [self.target],
            {"modbus": lambda t: None},
            announce=lambda *args: self.fail("must not announce"),
        )
        self.assertTrue(result["announcement_skipped"])


if __name__ == "__main__":
    unittest.main()
