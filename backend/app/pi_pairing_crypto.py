"""Crypto primitives for an *untrusted* BLE-discovered Pi's key possession.

Public key challenge success is NOT a trusted-device attestation. A separate
physical ownership confirmation and approved enrollment are required.
"""
import base64
import binascii
import re
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

HARDWARE_ID_RE = re.compile(r"^[a-zA-Z0-9:_-]{8,128}$")
DOMAIN = b"care-inspector-pi-pairing-v1\x00"


def decode_b64(data: str, expected_length: int) -> bytes:
    try:
        raw = base64.b64decode(data, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Malformed base64") from exc
    if len(raw) != expected_length:
        raise ValueError("Invalid cryptographic value length")
    return raw


def signed_message(pairing_id: str, hardware_id: str, challenge_b64: str) -> bytes:
    if not HARDWARE_ID_RE.fullmatch(hardware_id):
        raise ValueError("Invalid hardware identifier")
    challenge = decode_b64(challenge_b64, 32)
    return DOMAIN + pairing_id.encode("ascii") + b"\x00" + hardware_id.encode("ascii") + b"\x00" + challenge


def verify_pi_proof(
    public_key_b64: str,
    pairing_id: str,
    hardware_id: str,
    challenge_b64: str,
    signature_b64: str,
) -> bool:
    public_key = Ed25519PublicKey.from_public_bytes(decode_b64(public_key_b64, 32))
    signature = decode_b64(signature_b64, 64)
    message = signed_message(pairing_id, hardware_id, challenge_b64)
    try:
        public_key.verify(signature, message)
    except InvalidSignature:
        return False
    return True
