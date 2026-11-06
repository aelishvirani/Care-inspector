"""Mac-safe dry-run of Pi deployment layout and systemd startup contracts.

No systemd execution, no real credentials, no network, no printer commands.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from collector.pi_deployment_preflight import check_installation

ROOT = Path(__file__).resolve().parents[2]
UNITS = ROOT / "collector" / "systemd"
VENV_PYTHON = "/opt/care-inspector/.venv/bin/python"


class PiDeploymentSimulationTests(unittest.TestCase):
    def setUp(self):
        sandbox = tempfile.TemporaryDirectory()
        self.addCleanup(sandbox.cleanup)
        self.root = Path(sandbox.name)
        self.uid = os.getuid()

        self.python = self.root / VENV_PYTHON.lstrip("/")
        self.python.parent.mkdir(parents=True)
        self.python.write_text("# dummy python executable; never executed\n")
        self.python.chmod(0o755)

        self.state_dir = self.root / "var/lib/care-inspector"
        self.state_dir.mkdir(parents=True)
        self.state_dir.chmod(0o700)
        self.key = self.state_dir / "pi-ed25519.key"
        self.key.write_bytes(b"not a real private key")
        self.key.chmod(0o600)

        self.config_dir = self.root / "etc/care-inspector"
        self.config_dir.mkdir(parents=True)
        self.env = self.config_dir / "pi-cloud.env"
        self.env.write_text("CARE_INSPECTOR_BACKEND_URL=https://example.invalid\n")
        self.env.chmod(0o640)

    def preflight(self):
        return check_installation(self.root, service_uid=self.uid)

    def test_valid_mock_installation_passes_read_only_preflight(self):
        self.assertEqual(self.preflight(), [])
        self.assertTrue(self.key.exists())

    def test_missing_credentials_fail_before_deployment(self):
        self.key.unlink()
        self.env.unlink()
        problems = self.preflight()
        self.assertIn("Pi signing key is missing", problems)
        self.assertIn("Pi cloud environment is missing", problems)

    def test_insecure_permissions_fail_before_deployment(self):
        self.key.chmod(0o644)
        self.env.chmod(0o666)
        problems = self.preflight()
        self.assertIn("Pi signing key has unsafe permissions", problems)
        self.assertIn("Pi cloud environment has unsafe permissions", problems)

    def test_invalid_python_executable_fails_before_deployment(self):
        self.python.chmod(0o644)
        self.assertIn("Pi virtualenv Python is not executable", self.preflight())

    def test_cloud_services_require_same_install_paths_and_account(self):
        cases = {
            "care-inspector-cloud-heartbeat.service": "collector.pi_cloud_service",
            "care-inspector-printer-discovery.service": "collector.pi_printer_discovery",
            "care-inspector-pi-telemetry.service": "collector.pi_telemetry_service",
        }
        for name, module in cases.items():
            with self.subTest(unit=name):
                text = (UNITS / name).read_text()
                self.assertIn("User=careinspector\n", text)
                self.assertIn("Group=careinspector\n", text)
                self.assertIn("WorkingDirectory=/opt/care-inspector\n", text)
                self.assertIn("EnvironmentFile=/etc/care-inspector/pi-cloud.env\n", text)
                self.assertIn(f"ExecStart={VENV_PYTHON} -m {module}\n", text)
                self.assertIn("NoNewPrivileges=true\n", text)
                self.assertIn("ProtectSystem=strict\n", text)
                self.assertNotIn("collector.collector", text)

    def test_telemetry_startup_is_opt_in_and_restarts_only_for_transient_failure(self):
        text = (UNITS / "care-inspector-pi-telemetry.service").read_text()
        self.assertIn("After=network-online.target\n", text)
        self.assertIn("Restart=on-failure\n", text)
        self.assertIn("RestartPreventExitStatus=78\n", text)
        self.assertIn("StartLimitBurst=5\n", text)
        self.assertIn("WantedBy=multi-user.target\n", text)
        self.assertNotIn("ExecStartPre=/", text)
        self.assertNotIn("ExecStartPost=/", text)
        self.assertNotIn("systemctl enable", text)

    def test_discovery_timer_is_separate_from_telemetry(self):
        text = (UNITS / "care-inspector-printer-discovery.timer").read_text()
        self.assertIn("Unit=care-inspector-printer-discovery.service\n", text)
        self.assertNotIn("care-inspector-pi-telemetry.service", text)

    def test_ble_service_preserves_system_python_for_linux_bindings(self):
        text = (UNITS / "care-inspector-ble.service").read_text()
        self.assertIn("Requires=bluetooth.service\n", text)
        self.assertIn(
            "ExecStart=/usr/bin/python3 /opt/care-inspector/collector/pi_ble_gatt_server.py\n",
            text,
        )


if __name__ == "__main__":
    unittest.main()
