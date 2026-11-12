"""No-hardware tests of opt-in localhost BLE scanning and portal wiring."""
import asyncio
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from collector.local_ble_scanner import scan_nearby, HOST, PORT, ALLOWED_ORIGINS


class LocalBleScannerTests(unittest.TestCase):
    def test_scanner_is_loopback_only(self):
        self.assertEqual(HOST, "127.0.0.1")
        self.assertEqual(PORT, 8765)
        self.assertEqual(ALLOWED_ORIGINS, {
            "http://localhost:5173", "http://127.0.0.1:5173",
        })

    def test_scan_collects_advertisements_without_connecting(self):
        async def scenario():
            class FakeScanner:
                def __init__(self, detection_callback):
                    self.callback = detection_callback

                async def __aenter__(self):
                    self.callback(
                        types.SimpleNamespace(address="mac-opaque-1", name="Test BLE"),
                        types.SimpleNamespace(local_name=None, rssi=-45,
                                              service_uuids=["ABC"]),
                    )
                    return self

                async def __aexit__(self, *_):
                    return None

            fake_module = types.SimpleNamespace(BleakScanner=FakeScanner)
            with patch.dict(sys.modules, {"bleak": fake_module}):
                results = await scan_nearby(seconds=0)
            self.assertEqual(results, [{
                "id": "mac-opaque-1", "name": "Test BLE",
                "rssi": -45, "service_uuids": ["abc"],
            }])
        asyncio.run(scenario())

    def test_frontend_uses_local_proxy_but_preserves_browser_pairing(self):
        root = Path(__file__).resolve().parents[2]
        page = (root / "frontend/src/pages/RaspberryPiPage.jsx").read_text()
        vite = (root / "frontend/vite.config.js").read_text()
        self.assertIn("fetch('/local-ble/scan'", page)
        self.assertIn("navigator.bluetooth.requestDevice", page)
        self.assertIn("Select Pi for Verification", page)
        self.assertIn("target: 'http://127.0.0.1:8765'", vite)
        self.assertNotIn("http://127.0.0.1:8765", page)


if __name__ == "__main__":
    unittest.main()
