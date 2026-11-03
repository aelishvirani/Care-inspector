"""Read-only Hitachi printer detection tests; no Modbus hardware required."""
import asyncio
import unittest
from unittest.mock import AsyncMock

from collector.hitachi_identity_probe import (
    probe_hitachi_modbus, probe_hitachi_modbus_async,
)
from collector.printer_detection import (
    PrinterTarget, detect_configured_printers,
)


class HitachiIdentityProbeTests(unittest.TestCase):
    def setUp(self):
        self.target = PrinterTarget(
            host="127.0.0.1", port=1502,
            protocol="modbus", manufacturer="Hitachi",
        )
        self.driver = type("Driver", (), {})()
        self.driver.connect = AsyncMock(return_value=True)
        self.driver.read_identity = AsyncMock(return_value={
            "model_name": "UX2", "serial_number": 12345678
        })
        self.driver.disconnect = AsyncMock()
        self.created = []

        def factory(**kwargs):
            self.created.append(kwargs)
            return self.driver
        self.factory = factory

    def test_read_only_hitachi_identity(self):
        result = probe_hitachi_modbus(self.target, driver_factory=self.factory)
        self.assertEqual(result, {
            "model_name": "UX2", "serial_number": "12345678"
        })
        self.driver.connect.assert_awaited_once()
        self.driver.read_identity.assert_awaited_once()
        self.driver.disconnect.assert_awaited_once()
        self.assertEqual(self.created[0]["host"], "127.0.0.1")
        self.assertEqual(self.created[0]["port"], 1502)

    def test_discovery_registry_integration(self):
        printers = detect_configured_printers(
            [self.target],
            {"modbus": lambda target: probe_hitachi_modbus(
                target, driver_factory=self.factory
            )},
        )
        self.assertEqual(len(printers), 1)
        self.assertEqual(printers[0]["manufacturer"], "Hitachi")
        self.assertEqual(printers[0]["model_name"], "UX2")
        self.assertEqual(printers[0]["serial_number"], "12345678")

    def test_disconnected_not_identified(self):
        self.driver.connect = AsyncMock(return_value=False)
        self.assertIsNone(probe_hitachi_modbus(
            self.target, driver_factory=self.factory,
        ))
        self.driver.read_identity.assert_not_awaited()
        self.driver.disconnect.assert_awaited_once()

    def test_invalid_model_not_announced(self):
        self.driver.read_identity = AsyncMock(return_value={
            "model_name": "", "serial_number": 12345678
        })
        self.assertIsNone(probe_hitachi_modbus(
            self.target, driver_factory=self.factory,
        ))
        self.driver.disconnect.assert_awaited_once()

    def test_disconnect_even_if_read_fails(self):
        self.driver.read_identity = AsyncMock(side_effect=RuntimeError("Modbus error"))
        with self.assertRaises(RuntimeError):
            probe_hitachi_modbus(self.target, driver_factory=self.factory)
        self.driver.disconnect.assert_awaited_once()

    def test_incorrect_manufacturer_rejected(self):
        other = PrinterTarget(
            host="127.0.0.1", port=1502,
            protocol="modbus", manufacturer="Domino",
        )
        with self.assertRaises(ValueError):
            probe_hitachi_modbus(other, driver_factory=self.factory)
        self.assertEqual(self.created, [])

    def test_async_probe(self):
        result = asyncio.run(probe_hitachi_modbus_async(
            self.target, driver_factory=self.factory,
        ))
        self.assertEqual(result["model_name"], "UX2")


if __name__ == "__main__":
    unittest.main()
