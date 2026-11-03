"""Build a bounded, non-secret Raspberry Pi identity payload for BLE GATT.

This module is platform-independent and testable without a Raspberry Pi.
It does NOT advertise Bluetooth, prove ownership, or enroll the device.
"""
from __future__ import annotations

import json
import platform
import re
import socket
from pathlib import Path

HARDWARE_ID_FILE = Path("/proc/device-tree/serial-number")
CPUINFO_FILE = Path("/proc/cpuinfo")
MODEL_FILE = Path("/proc/device-tree/model")
NETWORK_DIRECTORY = Path("/sys/class/net")
MAC_PATTERN = re.compile(r"^(?:[0-9a-f]{2}:){5}[0-9a-f]{2}$")
SERVICE_UUID = "a18d7b10-f0e7-4d5e-8c1b-86e418d85001"
IDENTITY_UUID = "a18d7b11-f0e7-4d5e-8c1b-86e418d85001"


def read_text(path: Path) -> str:
    try:
        return path.read_bytes().replace(b"\x00", b"").decode("utf-8").strip()
    except (OSError, UnicodeError):
        return ""


def hardware_serial() -> str:
    serial = read_text(HARDWARE_ID_FILE)
    if serial:
        return serial
    text = read_text(CPUINFO_FILE)
    for line in text.splitlines():
        if line.lower().startswith("serial") and ":" in line:
            return line.split(":", 1)[1].strip()
    return ""


def network_mac() -> str:
    # Stable Ethernet MAC preferred over randomized Wi-Fi or Bluetooth MAC.
    for interface in ("eth0", "end0", "wlan0"):
        mac = read_text(NETWORK_DIRECTORY / interface / "address").lower()
        if MAC_PATTERN.fullmatch(mac) and mac != "00:00:00:00:00:00":
            return mac
    return ""


def identity_payload(
    hardware_id: str,
    hostname: str,
    model: str,
    mac_address: str = "",
) -> bytes:
    if not re.fullmatch(r"[a-zA-Z0-9:_-]{8,128}", hardware_id):
        raise ValueError("A stable hardware identifier is required")
    if not hostname or len(hostname) > 128:
        raise ValueError("Invalid hostname")
    if not model or len(model) > 128:
        raise ValueError("Invalid model")
    if mac_address and not MAC_PATTERN.fullmatch(mac_address.lower()):
        raise ValueError("Invalid MAC address")
    payload = {
        "hardware_id": hardware_id,
        "hostname": hostname,
        "model": model,
        "mac_address": mac_address.lower(),
        "protocol_version": "1",
    }
    encoded = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode()
    if len(encoded) > 512:
        raise ValueError("Pi identity payload exceeds BLE limit")
    return encoded


def collect_pi_identity() -> bytes:
    serial = hardware_serial()
    if not serial:
        raise RuntimeError("Pi hardware serial unavailable: must run on supported Raspberry Pi")
    model = read_text(MODEL_FILE)
    if not model or "raspberry pi" not in model.lower():
        raise RuntimeError("Raspberry Pi model unavailable")
    return identity_payload(
        hardware_id="pi-" + serial,
        hostname=socket.gethostname(),
        model=model,
        mac_address=network_mac(),
    )


if __name__ == "__main__":
    # Never print hardware ID or addresses into terminal logs by default.
    identity = collect_pi_identity()
    print(f"Pi identity payload ready ({len(identity)} bytes)")
