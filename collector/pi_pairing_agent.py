"""Raspberry Pi BLE key-possession signing primitives.

No network access, registration, or printer commands. This does NOT attest
device ownership: a remote or unapproved Pi could generate its own key.
"""
from __future__ import annotations

import base64
import json
import os
import tempfile
import time
from pathlib import Path
from threading import Lock

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding, NoEncryption, PrivateFormat, PublicFormat,
)

from backend.app.pi_pairing_crypto import signed_message

# Standard service-account writable directory on the Pi, NOT a Git directory.
DEFAULT_KEY_PATH = Path("/var/lib/care-inspector/pi-ed25519.key")
PUBLIC_KEY_UUID = "a18d7b12-f0e7-4d5e-8c1b-86e418d85001"
CHALLENGE_UUID = "a18d7b13-f0e7-4d5e-8c1b-86e418d85001"
PROOF_UUID = "a18d7b14-f0e7-4d5e-8c1b-86e418d85001"
MAX_CHALLENGE_BYTES = 350
PROOF_TTL_SECONDS = 90


def load_or_create_private_key(path: Path = DEFAULT_KEY_PATH) -> Ed25519PrivateKey:
    """Keep a persistent key: never silently regenerate if a present key is corrupt."""
    path = Path(path)
    if path.exists():
        if path.is_symlink():
            raise RuntimeError("Refusing symlinked pairing key")
        if path.stat().st_mode & 0o077:
            raise PermissionError("Pairing key permissions must be 0600")
        raw = path.read_bytes()
        if len(raw) != 32:
            raise ValueError("Invalid persisted pairing key")
        return Ed25519PrivateKey.from_private_bytes(raw)

    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    key = Ed25519PrivateKey.generate()
    raw = key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    # Exclusive create protects against accidentally overwriting existing key.
    try:
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return load_or_create_private_key(path)
    with os.fdopen(fd, "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    return key


def public_key_b64(key: Ed25519PrivateKey) -> str:
    raw = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return base64.b64encode(raw).decode("ascii")


class PairingSigner:
    """Single pending proof per agent; write challenge then read signature.

    Caller must bind the hardware ID to the Pi's actual hardware identity.
    Key possession alone is *not* a trusted device enrollment.
    """

    def __init__(self, key: Ed25519PrivateKey, hardware_id: str):
        self.key = key
        self.hardware_id = hardware_id
        self._lock = Lock()
        self._proof: bytes | None = None
        self._deadline = 0.0

    def accept_challenge(self, data: bytes) -> None:
        if len(data) > MAX_CHALLENGE_BYTES:
            raise ValueError("Challenge too large")
        try:
            request = json.loads(data.decode("utf-8"))
            if set(request) != {"pairing_id", "hardware_id", "challenge_b64"}:
                raise ValueError("Unexpected challenge fields")
            if request["hardware_id"] != self.hardware_id:
                raise ValueError("Challenge intended for another Pi")
            message = signed_message(
                request["pairing_id"], request["hardware_id"],
                request["challenge_b64"],
            )
        except (ValueError, UnicodeError, TypeError, KeyError, AttributeError) as exc:
            raise ValueError("Invalid pairing challenge") from exc
        proof = base64.b64encode(self.key.sign(message))
        with self._lock:
            self._proof = proof
            self._deadline = time.monotonic() + PROOF_TTL_SECONDS

    def read_proof(self, offset: int = 0) -> bytes:
        with self._lock:
            if self._proof is None or time.monotonic() >= self._deadline:
                self._proof = None
                raise ValueError("No active pairing proof")
            if offset < 0 or offset > len(self._proof):
                raise ValueError("Invalid proof offset")
            # Retain the proof during ATT long reads; expire quickly.
            return self._proof[offset:]
