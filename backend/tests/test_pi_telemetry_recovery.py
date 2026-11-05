"""Offline/recovery regression for signed Pi monitoring.

No production DB, hardware, printer commands, or legacy collector changes.
"""
import asyncio
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch

from sqlalchemy import select

from backend.app.models import Alert, Device, Measurement
from collector.pi_telemetry_service import monitor_one_printer
from collector.printer_detection import PrinterTarget


class PiTelemetryRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.target = PrinterTarget(
            host="127.0.0.1", port=1502, protocol="modbus",
            manufacturer="Hitachi",
        )
        self.printer_id = "printer-recovery-001"
        self.reading = {
            "device_id": self.printer_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "printing", "print_count": 20,
            "temperature_c": 25.0, "pressure_mpa": 0.25,
            "ink_level_percent": 90, "makeup_level_percent": 90,
        }

    def test_printer_read_failure_reconnects_and_resumes(self):
        async def scenario():
            stopped = False
            first = Mock(
                connect=AsyncMock(return_value=True),
                read_measurement=AsyncMock(side_effect=ConnectionError("cable unplugged")),
                disconnect=AsyncMock(),
            )
            second = Mock(
                connect=AsyncMock(return_value=True),
                read_measurement=AsyncMock(return_value=self.reading),
                disconnect=AsyncMock(),
            )
            drivers = iter([first, second])
            waits = []
            async def sleep(seconds):
                waits.append(seconds)
            def send(url, reading):
                nonlocal stopped
                stopped = True
                return {"status": "stored", "device_id": self.printer_id}
            await monitor_one_printer(
                "https://example.invalid", self.target, self.printer_id,
                build_driver=lambda *args, **kwargs: next(drivers),
                send=send, should_stop=lambda: stopped, sleep=sleep,
            )
            self.assertEqual(waits, [5])
            first.disconnect.assert_awaited_once()
            second.disconnect.assert_awaited_once()
            second.read_measurement.assert_awaited_once()
        asyncio.run(scenario())

    def test_cloud_interruption_reconnects_and_sends_fresh_reading(self):
        async def scenario():
            stopped = False
            first_read = dict(self.reading, print_count=20)
            second_read = dict(self.reading, print_count=21)
            first = Mock(
                connect=AsyncMock(return_value=True),
                read_measurement=AsyncMock(return_value=first_read),
                disconnect=AsyncMock(),
            )
            second = Mock(
                connect=AsyncMock(return_value=True),
                read_measurement=AsyncMock(return_value=second_read),
                disconnect=AsyncMock(),
            )
            drivers = iter([first, second])
            sent = []
            waits = []
            async def sleep(seconds):
                waits.append(seconds)
            def send(url, reading):
                nonlocal stopped
                sent.append(reading["print_count"])
                if len(sent) == 1:
                    raise ConnectionError("cloud disconnected")
                stopped = True
                return {"status": "stored", "device_id": self.printer_id}
            await monitor_one_printer(
                "https://example.invalid", self.target, self.printer_id,
                build_driver=lambda *args, **kwargs: next(drivers),
                send=send, should_stop=lambda: stopped, sleep=sleep,
            )
            self.assertEqual(sent, [20, 21])
            self.assertEqual(waits, [5])
            first.disconnect.assert_awaited_once()
            second.disconnect.assert_awaited_once()
        asyncio.run(scenario())

    def test_backend_offline_alert_resolves_after_new_signed_telemetry(self):
        # Reuse the secure Pi fixture with a separate in-memory database.
        from backend.tests.test_pi_telemetry import PiTelemetryTests
        from backend.app import main
        from backend.app import alerts

        fixture = PiTelemetryTests(
            methodName="test_authenticated_assigned_pi_stores_measurement",
        )
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        with fixture.session() as db:
            device = db.get(Device, fixture.device_id)
            device.last_seen = datetime.now(timezone.utc) - timedelta(seconds=60)
            device.online = True
            db.commit()

        # Single actual offline-monitor iteration, without waiting 5 seconds.
        # Keep alert creation and resolution real, suppress external notifications.
        async def one_cycle():
            calls = 0
            async def sleep(seconds):
                nonlocal calls
                calls += 1
                if calls > 1:
                    raise asyncio.CancelledError()
            with (
                patch.object(main, "SessionLocal", fixture.session),
                patch.object(main.asyncio, "sleep", sleep),
                patch.object(alerts, "notify_new_alert"),
                patch.object(alerts, "log_audit"),
            ):
                with self.assertRaises(asyncio.CancelledError):
                    await main.offline_monitor()
        asyncio.run(one_cycle())

        with fixture.session() as db:
            self.assertFalse(db.get(Device, fixture.device_id).online)
            offline = db.scalar(select(Alert).where(
                Alert.device_id == fixture.device_id,
                Alert.alert_type == "offline",
                Alert.active.is_(True),
            ))
            self.assertIsNotNone(offline)

        with (patch.object(alerts, "log_audit"),
              patch.object(alerts, "notify_new_alert")):
            response, _, _ = fixture.send(
                measurement=fixture.payload(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    print_count=888,
                ),
            )
        self.assertEqual(response.status_code, 200, response.text)
        with fixture.session() as db:
            device = db.get(Device, fixture.device_id)
            self.assertTrue(device.online)
            self.assertEqual(device.customer_id, 42)
            self.assertEqual(device.print_count, 888)
            self.assertEqual(db.scalar(select(Measurement).where(
                Measurement.device_id == fixture.device_id,
            )).print_count, 888)
            offline = db.scalar(select(Alert).where(
                Alert.device_id == fixture.device_id,
                Alert.alert_type == "offline",
            ))
            self.assertFalse(offline.active)
            self.assertIsNotNone(offline.resolved_at)


if __name__ == "__main__":
    unittest.main()
