"""Static deployment-contract tests; no systemd or Raspberry Pi required."""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SYSTEMD = ROOT / "collector" / "systemd"


class PiDiscoveryTimerTests(unittest.TestCase):
    def test_timer_starts_after_boot_and_repeats(self):
        text = (SYSTEMD / "care-inspector-printer-discovery.timer").read_text()
        self.assertIn("OnBootSec=90s", text)
        self.assertIn("OnUnitInactiveSec=5min", text)
        self.assertIn("RandomizedDelaySec=30s", text)
        self.assertIn("Unit=care-inspector-printer-discovery.service", text)

    def test_unit_runs_discovery_only(self):
        text = (SYSTEMD / "care-inspector-printer-discovery.service").read_text()
        self.assertIn("Type=oneshot", text)
        self.assertIn("User=careinspector", text)
        self.assertIn("ExecStart=/usr/bin/python3 -m collector.pi_printer_discovery", text)
        self.assertIn("EnvironmentFile=/etc/care-inspector/pi-cloud.env", text)
        self.assertNotIn("collector.collector", text)
        self.assertNotIn("printer-control", text.lower().split("execstart=")[-1].split("\n")[0])

    def test_setup_requires_explicit_targets(self):
        text = (ROOT / "collector" / "PI_DISCOVERY_SETUP.md").read_text()
        self.assertIn("CARE_INSPECTOR_PRINTER_TARGETS=", text)
        self.assertIn("printers.json", text)
        self.assertIn("not yet tested", text.lower())


if __name__ == "__main__":
    unittest.main()
