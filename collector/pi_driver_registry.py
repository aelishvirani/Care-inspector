"""Allowlisted, read-only telemetry driver factories for a single Pi printer.

Adding a manufacturer means registering a vetted adapter implementing the
existing PrinterDriver interface. No simulator or control channels are used.
"""
from __future__ import annotations

from .printer_detection import PrinterTarget, _validate_target


def build_pi_driver(target: PrinterTarget, *, printer_id: str):
    _validate_target(target)
    if not printer_id or not isinstance(printer_id, str):
        raise ValueError("A confirmed printer inventory ID is required")
    key = (target.manufacturer.casefold(), target.protocol.casefold())
    if key == ("hitachi", "modbus"):
        from .printers.hitachi_modbus import HitachiModbusPrinter
        return HitachiModbusPrinter(
            host=target.host, port=target.port, device_id=1,
            printer_id=printer_id,
        )
    raise ValueError("No approved Pi telemetry driver for this manufacturer/protocol")
