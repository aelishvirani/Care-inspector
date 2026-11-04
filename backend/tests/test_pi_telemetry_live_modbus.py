"""Opt-in integration: real localhost Modbus TCP -> signed API -> isolated SQLite.

Requires the existing simulator listening at 127.0.0.1:1502.
Does not touch the running backend, application database, or legacy collector.
Run with CARE_INSPECTOR_LIVE_MODBUS_TEST=1; otherwise this test is skipped.
"""
import asyncio
import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from sqlalchemy import select

from backend.app import pi_cloud_auth_api
from backend.app.models import Device, Measurement
from collector.pi_telemetry_client import send_measurement
from collector.pi_telemetry_service import monitor_one_printer
from collector.printer_detection import PrinterTarget
from collector.printers.simulator import SimulatorPrinter


class LiveModbusSignedTelemetryTests(unittest.TestCase):
    @unittest.skipUnless(
        os.getenv("CARE_INSPECTOR_LIVE_MODBUS_TEST") == "1",
        "Explicitly enable only while localhost Modbus simulator is running",
    )
    def test_real_modbus_to_signed_ingestion_isolated_database(self):
        # Import within the test so unittest discovery does not re-discover
        # the imported test fixture as additional tests in this module.
        from backend.tests.test_pi_telemetry import PiTelemetryTests

        fixture = PiTelemetryTests(
            methodName="test_authenticated_assigned_pi_stores_measurement"
        )
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.addCleanup(fixture.tearDown) if hasattr(fixture, "tearDown") else None
        fixture.client.app.include_router(pi_cloud_auth_api.router)
        auth_patch = patch.object(pi_cloud_auth_api, "SessionLocal", fixture.session)
        auth_patch.start()
        self.addCleanup(auth_patch.stop)

        target = PrinterTarget(
            host="127.0.0.1", port=1502, manufacturer="Hitachi",
            protocol="modbus", device_id=fixture.device_id,
        )
        stopped = False

        def post(url, path, payload):
            self.assertEqual(url, "http://127.0.0.1:8000")
            response = fixture.client.post(path, json=payload)
            if response.status_code >= 400:
                raise PermissionError(f"Isolated telemetry API returned {response.status_code}")
            return response.json()

        def send(backend_url, reading):
            nonlocal stopped
            self.assertEqual(reading["source"], "simulator")
            self.assertEqual(reading["device_id"], fixture.device_id)
            result = send_measurement(
                backend_url, fixture.hardware_id, fixture.key, reading, post=post,
            )
            stopped = True
            return result

        async def run_once():
            await monitor_one_printer(
                "http://127.0.0.1:8000", target, fixture.device_id,
                build_driver=lambda *_args, **_kwargs: SimulatorPrinter(
                    host="127.0.0.1", port=1502, device_id=1,
                    printer_id=fixture.device_id,
                ),
                send=send, should_stop=lambda: stopped,
            )

        # Real Modbus TCP read from the existing simulator; no remote commands.
        asyncio.run(asyncio.wait_for(run_once(), timeout=20))
        with fixture.session() as db:
            rows = db.scalars(select(Measurement)).all()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].device_id, fixture.device_id)
            self.assertEqual(rows[0].source, "hitachi_modbus")
            self.assertIsNotNone(rows[0].print_count)
            self.assertGreater(rows[0].temperature_c, -100)
            device = db.get(Device, fixture.device_id)
            self.assertTrue(device.online)
            self.assertEqual(device.customer_id, 42)
            self.assertEqual(device.print_count, rows[0].print_count)


if __name__ == "__main__":
    unittest.main()
