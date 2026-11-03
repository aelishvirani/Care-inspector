"""Domain-separated Ed25519 cloud authentication, distinct from BLE pairing."""
import base64
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from .pi_pairing_crypto import HARDWARE_ID_RE, decode_b64

DOMAIN = b"care-inspector-pi-cloud-auth-v1\x00"


def cloud_message(challenge_id: str, hardware_id: str, nonce_b64: str) -> bytes:
    if not HARDWARE_ID_RE.fullmatch(hardware_id):
        raise ValueError("Invalid hardware ID")
    # Our challenge IDs are UUIDs (36 ASCII characters).
    if len(challenge_id) != 36 or not all(
        c in "0123456789abcdef-" for c in challenge_id.lower()
    ):
        raise ValueError("Invalid challenge ID")
    nonce = decode_b64(nonce_b64, 32)
    return (DOMAIN + challenge_id.encode("ascii") + b"\x00" +
            hardware_id.encode("ascii") + b"\x00" + nonce)


def verify_cloud_signature(
    public_key_b64: str, challenge_id: str, hardware_id: str,
    nonce_b64: str, signature_b64: str,
) -> bool:
    key = Ed25519PublicKey.from_public_bytes(decode_b64(public_key_b64, 32))
    signature = decode_b64(signature_b64, 64)
    try:
        key.verify(signature, cloud_message(challenge_id, hardware_id, nonce_b64))
        return True
    except InvalidSignature:
        return False
