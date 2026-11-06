"""Opt-in, single-printer Pi telemetry worker.

No changes to simulator collector, WebSocket or printer-control service.
Uses the existing read-only PrinterDriver interface; only allowlisted drivers
can be constructed. Never scans subnets or creates a Pi signing key.
"""
from __future__ import annotations

import asyncio
import logging
import os
import signal
from pathlib import Path

from .pi_cloud_service import load_service_settings
from .pi_driver_registry import build_pi_driver
from .pi_printer_discovery import load_targets, fetch_remote_targets
from .pi_telemetry_client import send_from_pi
from .printer_detection import PrinterTarget, detect_configured_printers
from .hitachi_identity_probe import probe_hitachi_modbus

LOG = logging.getLogger(__name__)


def get_single_target(backend_url: str, environ=None) -> PrinterTarget:
    """Use the existing opt-in target sources; never guess an arbitrary IP."""
    env = os.environ if environ is None else environ
    source = env.get("CARE_INSPECTOR_PRINTER_CONFIG_SOURCE", "local").strip()
    if source == "local":
        filename = env.get("CARE_INSPECTOR_PRINTER_TARGETS", "").strip()
        if not filename:
            raise ValueError("Printer target file is required")
        targets = load_targets(filename)
    elif source == "cloud":
        targets = fetch_remote_targets(backend_url)
    elif source == "direct-link":
        from .pi_direct_link import passive_direct_link_target
        target = passive_direct_link_target(
            interface=env.get("CARE_INSPECTOR_PRINTER_INTERFACE", "eth0").strip()
        )
        targets = [target] if target is not None else []
    else:
        raise ValueError("Unknown printer target source")
    if len(targets) != 1:
        raise ValueError("Exactly one discovered printer target is required")
    return targets[0]


def identify_single_printer(target: PrinterTarget, *, probe=probe_hitachi_modbus) -> str:
    """Derive exactly the same printer ID as signed inventory discovery."""
    # Future manufacturers register an audited read-only identity probe.
    if (target.manufacturer.casefold(), target.protocol.casefold()) != ("hitachi", "modbus"):
        raise ValueError("No approved identity probe for printer")
    inventory = detect_configured_printers([target], {"modbus": probe})
    if len(inventory) != 1:
        raise ConnectionError("Printer identity not confirmed")
    return inventory[0]["device_id"]


async def monitor_one_printer(
    backend_url: str, target: PrinterTarget, printer_id: str,
    *, build_driver=build_pi_driver, send=send_from_pi,
    interval_seconds: float = 5, retry_seconds: float = 5,
    should_stop=lambda: False, sleep=asyncio.sleep,
) -> None:
    """Read and send serially; no parallel writes, command channel or stale queue.

    A cloud rejection is fatal. Transient failures reconnect and take a *new*
    reading; we never retry an old timestamp outside the backend's 120s window.
    """
    if not 1 <= interval_seconds <= 3600 or not 1 <= retry_seconds <= 3600:
        raise ValueError("Invalid collection/retry interval")
    while not should_stop():
        driver = build_driver(target, printer_id=printer_id)
        try:
            # Driver contract permits None on successful connection.
            # An explicit False indicates connection failure.
            if await driver.connect() is False:
                raise ConnectionError("Printer unavailable")
            while not should_stop():
                reading = await driver.read_measurement()
                if reading.get("device_id") != printer_id:
                    raise ValueError("Driver returned unexpected printer identity")
                # Signed client strips vendor-only fields and transmits only
                # the common telemetry schema. Do blocking HTTPS off event loop.
                result = await asyncio.to_thread(send, backend_url, reading)
                if result.get("status") != "stored" or result.get("device_id") != printer_id:
                    raise PermissionError("Cloud did not acknowledge the expected printer")
                if not should_stop():
                    await sleep(interval_seconds)
        except asyncio.CancelledError:
            raise
        except (PermissionError, FileNotFoundError, ValueError):
            # Never retry a broken identity, bad configuration, or denied access.
            raise
        except (ConnectionError, TimeoutError, OSError, RuntimeError) as exc:
            LOG.warning("Pi telemetry interrupted: %s", type(exc).__name__)
            if not should_stop():
                await sleep(retry_seconds)
        finally:
            await driver.disconnect()


async def run_service(environ=None, *, get_target=get_single_target,
                      identify=identify_single_printer,
                      monitor=monitor_one_printer, stop=None):
    backend_url, _ = load_service_settings(environ)
    env = os.environ if environ is None else environ
    interval = int(env.get("CARE_INSPECTOR_PI_TELEMETRY_SECONDS", "5"))
    if not 1 <= interval <= 3600:
        raise ValueError("Telemetry interval must be 1–3600 seconds")
    if stop is None:
        stop = asyncio.Event()
    # A printer may still be booting (or the cloud target source may be
    # temporarily unreachable). Keep the process alive rather than exhausting
    # systemd's restart limit. Never retry bad configuration or denied access.
    while not stop.is_set():
        try:
            target = await asyncio.to_thread(get_target, backend_url, env)
            printer_id = await asyncio.to_thread(identify, target)
        except (PermissionError, FileNotFoundError, ValueError):
            raise
        except (ConnectionError, TimeoutError, OSError) as exc:
            LOG.warning("Pi telemetry startup interrupted: %s", type(exc).__name__)
            try:
                await asyncio.wait_for(stop.wait(), timeout=5)
            except asyncio.TimeoutError:
                pass
            continue
        if stop.is_set():
            break
        await monitor(
            backend_url, target, printer_id,
            interval_seconds=interval, should_stop=stop.is_set,
        )
        return


def main():
    logging.basicConfig(level=logging.INFO)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    stop = asyncio.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            pass
    try:
        loop.run_until_complete(run_service(stop=stop))
    finally:
        loop.close()


if __name__ == "__main__":
    main()
