"""Sign discovered printer inventory with the Pi's registered private key.

The collector must obtain actual printer metadata locally; this module only
transports explicitly supplied inventory and never probes printer networks.
No bearer token or printer control permission is created.
"""
import base64
import hashlib
import json
from pathlib import Path

from .pi_cloud_auth_client import cloud_message, post_json
from .pi_pairing_agent import DEFAULT_KEY_PATH, load_or_create_private_key
from .pi_identity import hardware_serial, network_mac

DOMAIN = b"care-inspector-pi-signed-discovery-v1\x00"
FIELDS = ("device_id", "display_name", "manufacturer", "model_name",
          "serial_number", "protocol")


def normalize_inventory(mac_address: str, printers: list[dict]) -> dict:
    if not isinstance(printers, list) or len(printers) > 1:
        raise ValueError("Expected at most one printer per Raspberry Pi")
    # Match Pydantic's normalization and default-valued optional properties.
    normalized = []
    for printer in printers:
        if not isinstance(printer, dict) or set(printer) - set(FIELDS):
            raise ValueError("Invalid printer fields")
        if not isinstance(printer.get("device_id"), str):
            raise ValueError("Printer device_id required")
        normalized.append({
            field: printer.get(field) for field in FIELDS
        })
    return {"mac_address": mac_address, "printers": normalized}


def discovery_message(challenge_id: str, hardware_id: str,
                      nonce_b64: str, announcement: dict) -> bytes:
    canonical = json.dumps(
        announcement, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("ascii")
    return (DOMAIN + cloud_message(challenge_id, hardware_id, nonce_b64) +
            b"\x00" + hashlib.sha256(canonical).digest())


def announce_printers(backend_url: str, hardware_id: str, key,
                      mac_address: str, printers: list[dict], *,
                      post=post_json) -> dict:
    announcement = normalize_inventory(mac_address, printers)
    challenge = post(
        backend_url, "/api/pi-auth/challenge", {"hardware_id": hardware_id}
    )
    message = discovery_message(
        challenge["challenge_id"], hardware_id, challenge["nonce_b64"],
        announcement,
    )
    signature = base64.b64encode(key.sign(message)).decode("ascii")
    return post(backend_url, "/api/pi-discovery/announce", {
        "hardware_id": hardware_id,
        "challenge_id": challenge["challenge_id"],
        "signature_b64": signature,
        "announcement": announcement,
    })


def announce_from_pi(backend_url: str, printers: list[dict],
                     key_path: Path = DEFAULT_KEY_PATH) -> dict:
    if not key_path.is_file():
        raise FileNotFoundError("Registered Pi key missing")
    serial = hardware_serial()
    mac = network_mac()
    if not serial or not mac:
        raise RuntimeError("Pi hardware serial and MAC required for discovery")
    key = load_or_create_private_key(key_path)
    return announce_printers(
        backend_url, "pi-" + serial, key, mac, printers,
    )
