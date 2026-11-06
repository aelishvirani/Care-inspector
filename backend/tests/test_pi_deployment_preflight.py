"""Read-only Raspberry Pi deployment preflight tests on a disposable filesystem."""
import os
import tempfile
import unittest
from pathlib import Path

from collector.pi_deployment_preflight import check_installation


class PiDeploymentPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.uid = os.getuid()
        python = self.root / "opt/care-inspector/.venv/bin/python"
        python.parent.mkdir(parents=True)
        python.write_text("# mock executable; never run")
        python.chmod(0o755)
        state = self.root / "var/lib/care-inspector"
        state.mkdir(parents=True)
        state.chmod(0o700)
        key = state / "pi-ed25519.key"
        key.write_bytes(b"dummy fake key; never valid")
        key.chmod(0o600)
        env = self.root / "etc/care-inspector/pi-cloud.env"
        env.parent.mkdir(parents=True)
        env.write_text("CARE_INSPECTOR_BACKEND_URL=https://example.invalid\n")
        env.chmod(0o640)
        self.key = key
        self.env = env

    def check(self):
        return check_installation(self.root, service_uid=self.uid)

    def test_secure_dry_run_layout_passes(self):
        self.assertEqual(self.check(), [])

    def test_missing_key_fails_without_disclosing_content(self):
        self.key.unlink()
        problems = self.check()
        self.assertTrue(any("signing key is missing" in p for p in problems))
        self.assertNotIn("dummy fake", str(problems))

    def test_world_readable_key_fails(self):
        self.key.chmod(0o644)
        self.assertTrue(any("signing key has unsafe permissions" in p
                            for p in self.check()))

    def test_symlinked_key_is_rejected(self):
        self.key.unlink()
        self.key.symlink_to(self.env)
        self.assertTrue(any("signing key must be a regular file" in p
                            for p in self.check()))

    def test_group_writable_cloud_env_is_rejected(self):
        self.env.chmod(0o660)
        self.assertTrue(any("environment has unsafe permissions" in p
                            for p in self.check()))

    def test_missing_python_executable_fails(self):
        (self.root / "opt/care-inspector/.venv/bin/python").unlink()
        self.assertIn("Pi virtualenv Python is missing", self.check())

    def test_insecure_key_directory_fails(self):
        (self.root / "var/lib/care-inspector").chmod(0o755)
        self.assertTrue(any("key directory requires" in p for p in self.check()))


if __name__ == "__main__":
    unittest.main()
