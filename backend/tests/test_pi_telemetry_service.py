"""Isolated Pi runner tests; all printer I/O and cloud sending are mocked."""
import asyncio
import unittest
from unittest.mock import AsyncMock, Mock, patch

from collector.pi_telemetry_service import (
    get_single_target, identify_single_printer, monitor_one_printer, run_service,
)
from collector.pi_driver_registry import build_pi_driver
from collector.printer_detection import PrinterTarget


class PiTelemetryServiceTests(unittest.TestCase):
    def setUp(self):
        self.target = PrinterTarget(host="192.168.1.25", port=502,
                                    protocol="modbus", manufacturer="Hitachi")
        self.printer_id = "printer-abc123"
        self.reading = {
            "device_id": self.printer_id, "timestamp": "2026-11-04T10:00:00Z",
            "source": "hitachi_modbus", "online": True, "status": "printing",
            "print_count": 100, "temperature_c": 25.0, "pressure_mpa": 0.25,
        }

    def test_unknown_manufacturer_fails_closed_before_factory(self):
        foreign = PrinterTarget(host="192.168.1.25", port=502,
                                protocol="modbus", manufacturer="Videojet")
        with self.assertRaises(ValueError):
            build_pi_driver(foreign, printer_id=self.printer_id)

    def test_identity_must_be_confirmed(self):
        with self.assertRaises(ConnectionError):
            identify_single_printer(self.target, probe=lambda target: None)

    def test_identity_matches_discovery_id(self):
        identity = identify_single_printer(
            self.target, probe=lambda target: {
                "model_name": "UX2", "serial_number": "123456",
            },
        )
        self.assertTrue(identity.startswith("printer-"))

    def test_target_selection_never_chooses_two_printers(self):
        with patch("collector.pi_telemetry_service.load_targets",
                   return_value=[self.target, self.target]):
            with self.assertRaises(ValueError):
                get_single_target("https://example.invalid", {
                    "CARE_INSPECTOR_PRINTER_CONFIG_SOURCE": "local",
                    "CARE_INSPECTOR_PRINTER_TARGETS": "/fake",
                })

    def test_no_direct_link_does_not_scan_or_start(self):
        with patch("collector.pi_direct_link.passive_direct_link_target",
                   return_value=None):
            with self.assertRaises(ValueError):
                get_single_target("https://example.invalid", {
                    "CARE_INSPECTOR_PRINTER_CONFIG_SOURCE": "direct-link",
                })

    def test_one_reading_acknowledged_then_stops(self):
        async def scenario():
            stop = False
            driver = Mock()
            driver.connect = AsyncMock(return_value=True)
            driver.read_measurement = AsyncMock(return_value=self.reading)
            driver.disconnect = AsyncMock()
            sent = []
            def send(url, reading):
                nonlocal stop
                sent.append((url, reading))
                stop = True
                return {"status": "stored", "device_id": self.printer_id}
            await monitor_one_printer(
                "https://example.invalid", self.target, self.printer_id,
                build_driver=lambda *args, **kwargs: driver,
                send=send, should_stop=lambda: stop,
            )
            self.assertEqual(len(sent), 1)
            driver.disconnect.assert_awaited_once()
            driver.read_measurement.assert_awaited_once()
        asyncio.run(scenario())

    def test_cloud_rejection_never_retries(self):
        async def scenario():
            driver = Mock()
            driver.connect = AsyncMock(return_value=True)
            driver.read_measurement = AsyncMock(return_value=self.reading)
            driver.disconnect = AsyncMock()
            with self.assertRaises(PermissionError):
                await monitor_one_printer(
                    "https://example.invalid", self.target, self.printer_id,
                    build_driver=lambda *args, **kwargs: driver,
                    send=lambda *args: (_ for _ in ()).throw(PermissionError("Denied")),
                    sleep=AsyncMock(side_effect=AssertionError("Must not retry")),
                )
            driver.disconnect.assert_awaited_once()
        asyncio.run(scenario())

    def test_reconnects_after_printer_failure_with_fresh_read(self):
        async def scenario():
            stop = False
            first = Mock()
            first.connect = AsyncMock(return_value=False)
            first.disconnect = AsyncMock()
            second = Mock()
            second.connect = AsyncMock(return_value=True)
            second.read_measurement = AsyncMock(return_value=self.reading)
            second.disconnect = AsyncMock()
            drivers = iter([first, second])
            waits = []
            async def sleep(seconds):
                waits.append(seconds)
            def send(url, reading):
                nonlocal stop
                stop = True
                return {"status": "stored", "device_id": self.printer_id}
            await monitor_one_printer(
                "https://example.invalid", self.target, self.printer_id,
                build_driver=lambda *args, **kwargs: next(drivers),
                send=send, should_stop=lambda: stop, sleep=sleep,
            )
            self.assertEqual(waits, [5])
            first.disconnect.assert_awaited_once()
            second.disconnect.assert_awaited_once()
            second.read_measurement.assert_awaited_once()
        asyncio.run(scenario())

    def test_driver_identity_mismatch_never_sent(self):
        async def scenario():
            driver = Mock()
            driver.connect = AsyncMock(return_value=True)
            driver.read_measurement = AsyncMock(return_value={
                **self.reading, "device_id": "other-printer",
            })
            driver.disconnect = AsyncMock()
            with self.assertRaises(ValueError):
                await monitor_one_printer(
                    "https://example.invalid", self.target, self.printer_id,
                    build_driver=lambda *args, **kwargs: driver,
                    send=lambda *args: self.fail("Must not send mismatched identity"),
                )
            driver.disconnect.assert_awaited_once()
        asyncio.run(scenario())

    def test_service_passes_one_printer_and_interval(self):
        async def scenario():
            seen = {}
            async def monitor(url, target, pid, **kwargs):
                seen.update(url=url, target=target, printer_id=pid,
                            interval=kwargs["interval_seconds"])
            await run_service(
                environ={"CARE_INSPECTOR_BACKEND_URL": "https://example.invalid",
                         "CARE_INSPECTOR_PI_TELEMETRY_SECONDS": "7"},
                get_target=lambda *args: self.target,
                identify=lambda *args: self.printer_id,
                monitor=monitor,
            )
            self.assertEqual(seen["printer_id"], self.printer_id)
            self.assertEqual(seen["interval"], 7)
        asyncio.run(scenario())


    def test_transient_startup_failure_recovers_without_restarting_process(self):
        async def scenario():
            attempts = 0
            monitor_calls = []
            def select_target(*args):
                nonlocal attempts
                attempts += 1
                if attempts == 1:
                    raise ConnectionError("printer not ready")
                return self.target
            async def monitor(url, target, printer_id, **kwargs):
                monitor_calls.append((target, printer_id))
            with patch(
                "collector.pi_telemetry_service.asyncio.wait_for",
                new=AsyncMock(side_effect=asyncio.TimeoutError),
            ) as retry_wait:
                await run_service(
                    environ={"CARE_INSPECTOR_BACKEND_URL": "https://example.invalid"},
                    get_target=select_target,
                    identify=lambda target: self.printer_id,
                    monitor=monitor,
                )
            self.assertEqual(attempts, 2)
            self.assertEqual(monitor_calls, [(self.target, self.printer_id)])
            retry_wait.assert_awaited_once()
        asyncio.run(scenario())

    def test_shutdown_during_startup_retry_does_not_start_monitoring(self):
        async def scenario():
            stop = asyncio.Event()
            async def interrupt_wait(awaitable, timeout):
                stop.set()
                return await awaitable
            monitor = AsyncMock()
            with patch(
                "collector.pi_telemetry_service.asyncio.wait_for",
                side_effect=interrupt_wait,
            ):
                await run_service(
                    environ={"CARE_INSPECTOR_BACKEND_URL": "https://example.invalid"},
                    get_target=lambda *args: self.target,
                    identify=lambda *args: (_ for _ in ()).throw(
                        ConnectionError("printer offline")),
                    monitor=monitor,
                    stop=stop,
                )
            self.assertTrue(stop.is_set())
            monitor.assert_not_awaited()
        asyncio.run(scenario())

    def test_invalid_startup_configuration_fails_without_retry(self):
        async def scenario():
            with patch(
                "collector.pi_telemetry_service.asyncio.wait_for",
                new=AsyncMock(side_effect=AssertionError("Must not retry")),
            ):
                with self.assertRaises(ValueError):
                    await run_service(
                        environ={"CARE_INSPECTOR_BACKEND_URL": "https://example.invalid"},
                        get_target=lambda *args: (_ for _ in ()).throw(
                            ValueError("multiple printers")),
                    )
        asyncio.run(scenario())



if __name__ == "__main__":
    unittest.main()
