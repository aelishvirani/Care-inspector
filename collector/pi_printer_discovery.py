"""Explicitly configured Hitachi UX2 discovery -> signed Care-Inspector inventory.

Run on the Pi after BLE registration, not as an unauthenticated network scan.
The existing read-only Hitachi driver identifies the printer, and the Pi key
signs the result before the backend creates an unassigned inventory record.

No simulator fallback, printer writes, telemetry, or auto-enabling controls.
"""
from __future__ import annotations

import json
from pathlib import Path

from .hitachi_identity_probe import probe_hitachi_modbus
from .printer_detection import PrinterTarget, detect_and_announce, _validate_target
from .pi_cloud_service import load_service_settings


def parse_targets(data: dict) -> list[PrinterTarget]:
    """Validate local or remotely staged targets before any probe begins."""
    if not isinstance(data, dict) or set(data) != {"printers"}:
        raise ValueError("Expected a JSON object containing only printers")
    raw_targets = data["printers"]
    if not isinstance(raw_targets, list) or len(raw_targets) > 30:
        raise ValueError("Expected a list with at most 30 printers")
    targets = []
    for item in raw_targets:
        if not isinstance(item, dict):
            raise ValueError("Printer target must be an object")
        allowed = {"host", "port", "protocol", "manufacturer", "model_name",
                   "serial_number", "device_id"}
        if set(item) - allowed:
            raise ValueError("Unexpected printer target fields")
        if any(k not in item for k in ("host", "port", "protocol", "manufacturer")):
            raise ValueError("Printer target missing required settings")
        if type(item["port"]) is not int:
            raise ValueError("Printer port must be an integer")
        target = PrinterTarget(**item)
        _validate_target(target)
        if target.device_id:
            import re
            if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.:-]{2,99}", target.device_id):
                raise ValueError("Invalid configured printer ID")

        # Only the tested Hitachi Modbus probe is wired for now.
        if target.protocol != "modbus" or target.manufacturer.casefold() != "hitachi":
            raise ValueError("Only configured Hitachi Modbus targets supported")
        targets.append(target)
    return targets


def load_targets(path: str | Path) -> list[PrinterTarget]:
    """Read explicitly provisioned printer endpoints. No network scanning."""
    config_path = Path(path)
    return parse_targets(json.loads(config_path.read_text(encoding="utf-8")))


def fetch_remote_targets(backend_url: str, *, fetch=None) -> list[PrinterTarget]:
    """Explicit cloud opt-in: fetch in memory, fail closed on invalid data."""
    if fetch is None:
        # Lazy import keeps existing Pi configuration client independently usable.
        from .pi_config_client import fetch_from_pi
        fetch = fetch_from_pi
    response = fetch(backend_url)
    if not isinstance(response, dict):
        raise ValueError("Invalid cloud configuration response")
    if response.get("configuration_applied") is not False:
        raise ValueError("Unexpected cloud apply state")
    if type(response.get("version")) is not int or response["version"] < 0:
        raise ValueError("Invalid remote configuration version")
    return parse_targets({"printers": response.get("printers")})


def discover_configured_hitachi(backend_url: str, targets: list[PrinterTarget],
                                *, probe=probe_hitachi_modbus, announce=None) -> dict:
    """One read-only discovery cycle, signed if printer identity is confirmed."""
    return detect_and_announce(
        backend_url,
        targets,
        {"modbus": probe},
        announce=announce,
    )


def main() -> None:
    import os
    backend_url, _ = load_service_settings()
    source = os.environ.get("CARE_INSPECTOR_PRINTER_CONFIG_SOURCE", "local").strip()
    if source == "local":
        # Preserve the original local file workflow by default.
        config_path = os.environ.get("CARE_INSPECTOR_PRINTER_TARGETS", "").strip()
        if not config_path:
            raise ValueError("CARE_INSPECTOR_PRINTER_TARGETS must point to a JSON file")
        targets = load_targets(config_path)
    elif source == "cloud":
        # Deliberate deployment opt-in; never persist cloud targets to disk.
        targets = fetch_remote_targets(backend_url)
    else:
        raise ValueError("Printer config source must be local or cloud")
    result = discover_configured_hitachi(backend_url, targets)
    # Never print cloud secrets, private keys, IPs, or printer serial numbers.
    print("Printer discovery completed; announced:",
          sum(p.get("status") in {"unassigned", "known"}
              for p in result.get("printers", [])))


if __name__ == "__main__":
    main()
