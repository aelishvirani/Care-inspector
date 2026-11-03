"""Safe, modular printer detection for explicitly configured Pi-side endpoints.

No customer-network scanning, Modbus writes or printer-control commands.
Manufacturers can add read-only probes via the supplied protocol registry.
The result is compatible with pi_signed_discovery_client.announce_from_pi().
"""
from __future__ import annotations

import hashlib
import ipaddress
import re
from dataclasses import dataclass
from typing import Callable, Mapping


@dataclass(frozen=True)
class PrinterTarget:
    host: str
    port: int
    protocol: str
    manufacturer: str
    model_name: str = ""
    serial_number: str = ""
    device_id: str = ""


class PrinterProbeError(Exception):
    """Read-only probe could not identify a configured printer."""


def _validate_target(target: PrinterTarget) -> None:
    # IP literals only: no DNS rebinding and no arbitrary hostnames.
    try:
        addr = ipaddress.ip_address(target.host)
    except ValueError as exc:
        raise ValueError("Printer target must use a configured IP address") from exc
    if not (addr.is_private or addr.is_loopback or addr.is_link_local):
        raise ValueError("Printer target must be inside a local network")
    if not 1 <= target.port <= 65535:
        raise ValueError("Invalid printer port")
    if not re.fullmatch(r"[a-z0-9_-]{2,32}", target.protocol):
        raise ValueError("Invalid printer protocol")
    if not 1 <= len(target.manufacturer) <= 100:
        raise ValueError("Printer manufacturer is required")


def _stable_device_id(target: PrinterTarget, serial: str) -> str:
    # Serial-based inventory keys persist across an IP change. If no serial
    # is available, the configured endpoint is used; changing it may create
    # a new unassigned inventory item that requires reconciliation.
    source = (
        f"{target.manufacturer}|{serial}"
        if serial else
        f"{target.manufacturer}|{target.protocol}|{target.host}|{target.port}"
    )
    return "printer-" + hashlib.sha256(source.encode("utf-8")).hexdigest()[:24]


def detect_configured_printers(
    targets: list[PrinterTarget],
    probes: Mapping[str, Callable[[PrinterTarget], dict | None]],
) -> list[dict]:
    """Invoke read-only manufacturer/protocol probes on declared addresses.

    A probe must return a dict with optional model_name and serial_number, or
    None when no compatible printer responds. No inference from an open port.
    Never include IPs or credentials in the announced inventory metadata.
    """
    if len(targets) > 30:
        raise ValueError("At most 30 configured printers are allowed")
    devices = []
    used = set()
    for target in targets:
        _validate_target(target)
        probe = probes.get(target.protocol)
        if probe is None:
            raise PrinterProbeError(f"No read-only probe for protocol {target.protocol}")
        result = probe(target)
        if result is None:
            continue
        if not isinstance(result, dict):
            raise PrinterProbeError("Invalid printer probe result")
        serial = str(result.get("serial_number") or target.serial_number or "").strip()
        model = str(result.get("model_name") or target.model_name or "").strip()
        if len(serial) > 120 or len(model) > 100:
            raise PrinterProbeError("Printer identity exceeds supported length")
        device_id = target.device_id.strip() or _stable_device_id(target, serial)
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.:-]{2,99}", device_id):
            raise PrinterProbeError("Invalid configured printer ID")
        if device_id in used:
            raise PrinterProbeError("Duplicate printer identity")
        used.add(device_id)
        devices.append({
            "device_id": device_id,
            "display_name": (f"{target.manufacturer} {model}".strip())[:100],
            "manufacturer": target.manufacturer,
            "model_name": model or None,
            "serial_number": serial or None,
            "protocol": target.protocol,
        })
    return devices


def detect_and_announce(backend_url: str, targets: list[PrinterTarget],
                        probes: Mapping[str, Callable[[PrinterTarget], dict | None]],
                        *, announce=None) -> dict:
    """Detect confirmed printers, then report via the signed Pi identity.

    Empty detection is not reported as removal of existing inventory.
    """
    printers = detect_configured_printers(targets, probes)
    if not printers:
        return {"printers": [], "announcement_skipped": True}
    if announce is None:
        from .pi_signed_discovery_client import announce_from_pi
        announce = announce_from_pi
    return announce(backend_url, printers)
