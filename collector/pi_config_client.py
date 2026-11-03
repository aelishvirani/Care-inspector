"""Authenticated, read-only retrieval of staged Pi printer targets.

This only fetches and validates config in memory. Never changes the systemd
target file, probes endpoints, or authorizes printer commands.
"""
import base64
from pathlib import Path

from .pi_cloud_auth_client import cloud_message, post_json
from .pi_cloud_service import load_service_settings
from .pi_pairing_agent import DEFAULT_KEY_PATH, load_or_create_private_key
from .pi_identity import hardware_serial
from .pi_printer_discovery import load_targets

DOMAIN = b"care-inspector-pi-config-fetch-v1\x00"


def fetch_message(challenge_id: str, hardware_id: str, nonce_b64: str) -> bytes:
    return DOMAIN + cloud_message(challenge_id, hardware_id, nonce_b64)


def fetch_targets(backend_url: str, hardware_id: str, key, *, post=post_json) -> dict:
    challenge = post(backend_url, "/api/pi-auth/challenge", {
        "hardware_id": hardware_id,
    })
    proof = base64.b64encode(key.sign(fetch_message(
        challenge["challenge_id"], hardware_id, challenge["nonce_b64"],
    ))).decode("ascii")
    result = post(backend_url, "/api/pi-config/fetch", {
        "hardware_id": hardware_id,
        "challenge_id": challenge["challenge_id"],
        "signature_b64": proof,
    })
    if result.get("hardware_id") != hardware_id:
        raise PermissionError("Configuration belongs to a different Pi")
    if type(result.get("version")) is not int or result["version"] < 0:
        raise ValueError("Invalid configuration version")
    if not isinstance(result.get("printers"), list):
        raise ValueError("Invalid configuration printer list")
    if result.get("configuration_applied") is not False:
        raise ValueError("Unexpected auto-apply response")
    return result


def fetch_from_pi(backend_url: str, key_path: Path = DEFAULT_KEY_PATH) -> dict:
    if not key_path.is_file():
        raise FileNotFoundError("Registered Pi key missing")
    serial = hardware_serial()
    if not serial:
        raise RuntimeError("Pi hardware serial missing")
    key = load_or_create_private_key(key_path)
    return fetch_targets(backend_url, "pi-" + serial, key)
