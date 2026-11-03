"""Read-only Hitachi UX2 identity probe for configured Modbus TCP printers.

Reuse the existing driver and its documented input-register reads.
No probing by port opening alone; no writes, print commands or network scans.
"""
from __future__ import annotations

import asyncio

from .printer_detection import PrinterProbeError, PrinterTarget


async def probe_hitachi_modbus_async(target: PrinterTarget, *, device_id: int = 1,
                                    driver_factory=None) -> dict | None:
    if target.protocol != "modbus" or target.manufacturer.casefold() != "hitachi":
        raise ValueError("Not a Hitachi Modbus printer target")
    if not 1 <= device_id <= 247:
        raise ValueError("Invalid Modbus device address")

    if driver_factory is None:
        from .printers.hitachi_modbus import HitachiModbusPrinter
        driver_factory = HitachiModbusPrinter

    driver = driver_factory(
        host=target.host, port=target.port, device_id=device_id,
    )
    try:
        connected = await driver.connect()
        if not connected:
            return None
        identity = await driver.read_identity()
        # Require a positive identity read, not simply an open TCP port.
        model = str(identity.get("model_name") or "").strip()
        serial = identity.get("serial_number")
        if not model or serial is None or not str(serial).strip():
            return None
        return {"model_name": model, "serial_number": str(serial)}
    except (OSError, TimeoutError, ConnectionError):
        return None
    finally:
        await driver.disconnect()


def probe_hitachi_modbus(target: PrinterTarget, *, device_id: int = 1,
                         driver_factory=None) -> dict | None:
    """Synchronous protocol-registry adapter. Call outside an active event loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(
            probe_hitachi_modbus_async(
                target, device_id=device_id, driver_factory=driver_factory,
            )
        )
    raise PrinterProbeError("Call the async probe from an event loop instead")
