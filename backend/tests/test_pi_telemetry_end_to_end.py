"""End-to-end signed Pi telemetry: mocked printer, real HTTP routes, isolated SQLite.

No real printer, SIM, Raspberry Pi, network listener, or production database.
Exercises the production runner -> signed client -> challenge -> ingestion ->
persisted device/measurement path without changing the simulator collector.
"""
import asyncio
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

from sqlalchemy import select

from backend.app import pi_cloud_auth_api
from backend.app.models import Device, Measurement
from backend.app.pi_cloud_challenges import PiCloudChallenge
from backend.tests.test_pi_telemetry import PiTelemetryTests
from collector.pi_telemetry_client import send_measurement
from collector.pi_telemetry_service import monitor_one_printer
from collector.printer_detection import PrinterTarget


class PiTelemetryEndToEndTests(unittest.TestCase):
    def setUp(self):
        # Reuse the isolated, pre-registered and assigned Pi/printer fixture.
        # Do not run the fixture's own test methods again.
        self.fixture = PiTelemetryTests(
            methodName="test_authenticated_assigned_pi_stores_measurement"
        )
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.db = self.fixture.session
        self.fixture.client.app.include_router(pi_cloud_auth_api.router)
        p = patch.object(pi_cloud_auth_api, "SessionLocal", self.db)
        p.start()
        self.addCleanup(p.stop)
        self.target = PrinterTarget(
            host="127.0.0.1", port=1502, manufacturer="Hitachi",
            protocol="modbus", device_id=self.fixture.device_id,
        )

    def send_via_http(self, backend_url, reading):
        def post(url, path, payload):
            self.assertEqual(url, "https://test.invalid")
            response = self.fixture.client.post(path, json=payload)
            if response.status_code >= 400:
                raise PermissionError(f"Telemetry API returned {response.status_code}")
            return response.json()

        return send_measurement(
            backend_url, self.fixture.hardware_id, self.fixture.key, reading,
            post=post,
        )

    def test_real_signed_http_pipeline_persists_reading(self):
        async def scenario():
            stopped = False
            printer = Mock()
            printer.connect = AsyncMock(return_value=True)
            printer.disconnect = AsyncMock()
            printer.read_measurement = AsyncMock(return_value={
                "device_id": self.fixture.device_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "printing", "print_count": 712,
                "temperature_c": 26.2, "pressure_mpa": 0.252,
                "ink_level_percent": 79, "makeup_level_percent": 82,
                "source": "simulator", "online": True,
            })

            def send(url, reading):
                nonlocal stopped
                result = self.send_via_http(url, reading)
                stopped = True
                return result

            await monitor_one_printer(
                "https://test.invalid", self.target, self.fixture.device_id,
                build_driver=lambda *args, **kwargs: printer,
                send=send, should_stop=lambda: stopped,
            )
            printer.connect.assert_awaited_once()
            printer.read_measurement.assert_awaited_once()
            printer.disconnect.assert_awaited_once()

        asyncio.run(scenario())
        with self.db() as db:
            readings = db.scalars(select(Measurement)).all()
            self.assertEqual(len(readings), 1)
            self.assertEqual(readings[0].print_count, 712)
            self.assertEqual(readings[0].source, "hitachi_modbus")
            self.assertEqual(readings[0].temperature_c, 26.2)
            printer = db.get(Device, self.fixture.device_id)
            self.assertTrue(printer.online)
            self.assertEqual(printer.customer_id, 42)
            self.assertEqual(printer.status, "printing")
            challenges = db.scalars(select(PiCloudChallenge)).all()
            self.assertEqual(len(challenges), 1)
            self.assertEqual(challenges[0].state, "telemetry_stored")

    def test_verified_inventory_not_untrusted_source_controls_metadata(self):
        with self.db() as db:
            from backend.app.printer_discovery_links import PrinterDiscoveryLink
            link = db.get(PrinterDiscoveryLink, self.fixture.device_id)
            link.manufacturer = "Videojet"
            link.protocol = "ethernet"
            db.commit()

        result = self.send_via_http("https://test.invalid", {
            "device_id": self.fixture.device_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "ready", "print_count": 101,
            "temperature_c": 24.5, "pressure_mpa": 0.21,
            "source": "forged_client_label", "online": True,
        })
        self.assertEqual(result["status"], "stored")
        with self.db() as db:
            reading = db.scalars(select(Measurement)).one()
            device = db.get(Device, self.fixture.device_id)
            self.assertEqual(reading.source, "videojet_ethernet")
            self.assertEqual(device.source, "videojet_ethernet")


if __name__ == "__main__":
    unittest.main()
