"""Tests for safe, I/O-free command inspection."""
import unittest

from backend.app.command_protocol_validation import inspect_custom_command


class CommandProtocolValidationTests(unittest.TestCase):
    def test_valid_spaced_hex_is_not_executable(self):
        result = inspect_custom_command("00 01", protocol="modbus_tcp")
        self.assertTrue(result.valid_hex)
        self.assertEqual(result.byte_count, 2)
        self.assertFalse(result.executable)
        self.assertIn("register address", result.reason)

    def test_compact_hex_is_valid(self):
        result = inspect_custom_command("0001", protocol="modbus_tcp")
        self.assertTrue(result.valid_hex)
        self.assertEqual(result.byte_count, 2)
        self.assertFalse(result.executable)

    def test_invalid_hex_is_rejected(self):
        for value in ("", "0", "0Z", "0 1", "GG"):
            with self.subTest(value=value):
                result = inspect_custom_command(value)
                self.assertFalse(result.valid_hex)
                self.assertFalse(result.executable)

    def test_unknown_protocol_is_never_executable(self):
        result = inspect_custom_command("AABB", protocol="raw_tcp")
        self.assertTrue(result.valid_hex)
        self.assertFalse(result.executable)

    def test_max_length_guard(self):
        result = inspect_custom_command("AA" * 257)
        self.assertFalse(result.valid_hex)


if __name__ == "__main__":
    unittest.main()
