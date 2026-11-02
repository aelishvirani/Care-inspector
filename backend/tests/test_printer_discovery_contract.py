import unittest
from pydantic import ValidationError

from backend.app.collectors_api import DiscoveryAnnouncement, PrinterAnnouncement


class DiscoveryContractTests(unittest.TestCase):
    def test_printer_serial_is_text_not_forced_integer(self):
        result = PrinterAnnouncement(
            device_id="hitachi-ux2-123", serial_number="UX2-A0000123",
            manufacturer="Hitachi", model_name="UX2"
        )
        self.assertEqual(result.serial_number, "UX2-A0000123")

    def test_reject_too_many_reported_printers(self):
        with self.assertRaises(ValidationError):
            DiscoveryAnnouncement(
                mac_address="dc:a6:32:12:34:56",
                printers=[{"device_id": f"printer-{x}"} for x in range(31)],
            )


if __name__ == "__main__":
    unittest.main()
