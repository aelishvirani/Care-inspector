"""Signed, single-measurement Pi telemetry transport.

Opt-in adapter for a future Pi monitoring service. The simulator collector and
its WebSocket are not modified. Never generates keys or sends printer commands.
"""
import base64
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from .pi_cloud_auth_client import cloud_message, post_json
from .pi_identity import hardware_serial
from .pi_pairing_agent import DEFAULT_KEY_PATH, load_or_create_private_key

DOMAIN = b"care-inspector-pi-telemetry-v1\x00"
FIELDS = (
    "device_id", "timestamp", "status", "print_count",
    "temperature_c", "pressure_mpa", "ink_level_percent",
    "makeup_level_percent",
)


def normalize_measurement(reading: dict) -> dict:
    if not isinstance(reading, dict):
        raise ValueError("Measurement must be an object")
    if not isinstance(reading.get("device_id"), str) or not 3 <= len(reading["device_id"]) <= 100:
        raise ValueError("Invalid printer identity")
    status = reading.get("status")
    if not isinstance(status, str) or not 1 <= len(status) <= 80:
        raise ValueError("Invalid printer status")
    try:
        timestamp = datetime.fromisoformat(
            str(reading["timestamp"]).replace("Z", "+00:00")
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Invalid measurement timestamp") from exc
    if timestamp.tzinfo is None:
        raise ValueError("Measurement timestamp must have a UTC offset")
    timestamp = timestamp.astimezone(timezone.utc)
    result = {
        "device_id": reading["device_id"],
        "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
        "status": status,
    }
    for field in ("print_count", "ink_level_percent", "makeup_level_percent"):
        value = reading.get(field)
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError("Invalid numeric measurement")
        if field.endswith("_percent") and value is not None and value > 100:
            raise ValueError("Invalid percentage")
        result[field] = value
    for field in ("temperature_c", "pressure_mpa"):
        try:
            value = float(reading[field])
        except (TypeError, KeyError, ValueError) as exc:
            raise ValueError("Invalid required measurement") from exc
        if not math.isfinite(value):
            raise ValueError("Measurement must be finite")
        if field == "temperature_c" and not -100 <= value <= 200:
            raise ValueError("Invalid temperature")
        if field == "pressure_mpa" and not 0 <= value <= 10:
            raise ValueError("Invalid pressure")
        result[field] = value
    return result


def telemetry_message(challenge_id: str, hardware_id: str,
                      nonce_b64: str, reading: dict) -> bytes:
    encoded = json.dumps(
        reading, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("ascii")
    return (DOMAIN + cloud_message(challenge_id, hardware_id, nonce_b64) +
            b"\x00" + hashlib.sha256(encoded).digest())


def send_measurement(backend_url: str, hardware_id: str, key, reading: dict,
                     *, post=post_json) -> dict:
    measurement = normalize_measurement(reading)
    challenge = post(
        backend_url, "/api/pi-auth/challenge", {"hardware_id": hardware_id}
    )
    signature = base64.b64encode(key.sign(telemetry_message(
        challenge["challenge_id"], hardware_id, challenge["nonce_b64"], measurement,
    ))).decode("ascii")
    return post(backend_url, "/api/pi-telemetry/ingest", {
        "hardware_id": hardware_id,
        "challenge_id": challenge["challenge_id"],
        "signature_b64": signature,
        "measurement": measurement,
    })


def send_from_pi(backend_url: str, reading: dict,
                 key_path: Path = DEFAULT_KEY_PATH) -> dict:
    if not key_path.is_file():
        raise FileNotFoundError("Registered Pi signing key missing")
    serial = hardware_serial()
    if not serial:
        raise RuntimeError("Raspberry Pi hardware ID unavailable")
    key = load_or_create_private_key(key_path)
    return send_measurement(backend_url, "pi-" + serial, key, reading)
