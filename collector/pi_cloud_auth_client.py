"""Raspberry Pi outbound cloud identity proof (no persistent session yet).

Use the exact private key used by the BLE pairing service. This client
does not generate or overwrite that key and never sends it over HTTP.
The server returns key-possession verification only, not a session token.
"""
import base64
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .pi_pairing_agent import DEFAULT_KEY_PATH, HARDWARE_ID_RE, load_or_create_private_key

DOMAIN = b"care-inspector-pi-cloud-auth-v1\x00"


def cloud_message(challenge_id: str, hardware_id: str, nonce_b64: str) -> bytes:
    import uuid
    if not HARDWARE_ID_RE.fullmatch(hardware_id):
        raise ValueError("Invalid hardware identifier")
    try:
        if str(uuid.UUID(challenge_id)) != challenge_id.lower():
            raise ValueError("Invalid challenge identifier")
        nonce = base64.b64decode(nonce_b64, validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError("Invalid cloud challenge") from exc
    if len(nonce) != 32:
        raise ValueError("Invalid challenge nonce")
    return (DOMAIN + challenge_id.encode("ascii") + b"\x00" +
            hardware_id.encode("ascii") + b"\x00" + nonce)


def post_json(base_url: str, path: str, payload: dict, timeout: int = 10) -> dict:
    parsed = urlsplit(base_url)
    if parsed.scheme != "https" and not (
        parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    ):
        raise ValueError("Only HTTPS is allowed outside localhost")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Invalid backend URL")
    url = base_url.rstrip("/") + path
    req = Request(
        url, data=json.dumps(payload).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(req, timeout=timeout) as response:
            return json.load(response)
    except HTTPError as exc:
        # Authorization, malformed requests and rate limits are not network outages.
        # Retry server failures (5xx) only. Do not log response bodies or secrets.
        if 500 <= exc.code <= 599:
            raise ConnectionError("Care-Inspector server temporarily unavailable") from exc
        raise PermissionError("Care-Inspector rejected device authentication request") from exc
    except URLError as exc:
        raise ConnectionError("Care-Inspector authentication network unavailable") from exc


def authenticate_pi(hardware_id: str, post, key) -> dict:
    """Perform one server challenge and sign with the persistent Pi key.

    post(path, payload) -> response dictionary. It can be injected for tests.
    """
    if not HARDWARE_ID_RE.fullmatch(hardware_id):
        raise ValueError("Invalid hardware identifier")
    challenge = post("/api/pi-auth/challenge", {"hardware_id": hardware_id})
    challenge_id = challenge["challenge_id"]
    nonce_b64 = challenge["nonce_b64"]
    signature = key.sign(cloud_message(challenge_id, hardware_id, nonce_b64))
    proof = post("/api/pi-auth/prove", {
        "hardware_id": hardware_id,
        "challenge_id": challenge_id,
        "signature_b64": base64.b64encode(signature).decode("ascii"),
    })
    if proof.get("authenticated") is not True or proof.get("hardware_id") != hardware_id:
        raise PermissionError("Backend did not confirm Pi key authentication")
    return proof


def authenticate_from_pi(backend_url: str, key_path: Path = DEFAULT_KEY_PATH) -> dict:
    # Never create a replacement key for a Pi that is already registered.
    if not key_path.is_file():
        raise FileNotFoundError("Pi identity key missing; complete device setup first")
    from .pi_identity import hardware_serial
    serial = hardware_serial()
    if not serial:
        raise RuntimeError("Raspberry Pi hardware serial unavailable")
    key = load_or_create_private_key(key_path)
    return authenticate_pi(
        "pi-" + serial,
        lambda path, data: post_json(backend_url, path, data),
        key,
    )
