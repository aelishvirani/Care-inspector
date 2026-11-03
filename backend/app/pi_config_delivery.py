"""One-time Ed25519 authenticated, read-only Pi configuration delivery.

A registered Pi signs a fresh challenge for the *fetch-configuration* action.
No persistent bearer token, session, printer commands, or configuration apply.
"""
import base64
from datetime import datetime, timezone

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .database import SessionLocal
from .pi_cloud_challenges import PiCloudChallenge
from .pi_cloud_crypto import cloud_message
from .pi_pairing_crypto import decode_b64
from .pi_registered_devices import PiRegisteredDevice
from .pi_target_config import PiTargetConfiguration

router = APIRouter(prefix="/api/pi-config", tags=["pi-config-delivery"])
DOMAIN = b"care-inspector-pi-config-fetch-v1\x00"


class ConfigFetchProof(BaseModel):
    hardware_id: str = Field(min_length=8, max_length=128)
    challenge_id: str = Field(min_length=36, max_length=36)
    signature_b64: str = Field(min_length=88, max_length=88)


def fetch_message(challenge_id: str, hardware_id: str, nonce_b64: str) -> bytes:
    # Separate purpose from cloud heartbeat/discovery: no signature reuse.
    return DOMAIN + cloud_message(challenge_id, hardware_id, nonce_b64)


@router.post("/fetch")
def fetch_pi_configuration(request: ConfigFetchProof):
    with SessionLocal() as db:
        challenge = db.get(PiCloudChallenge, request.challenge_id)
        if challenge is None or challenge.hardware_id != request.hardware_id:
            raise HTTPException(404, "Challenge unavailable")
        if challenge.state != "pending":
            raise HTTPException(409, "Challenge already used")
        expires_at = challenge.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) >= expires_at:
            challenge.state = "expired"
            db.commit()
            raise HTTPException(410, "Challenge expired")

        device = db.get(PiRegisteredDevice, request.hardware_id)
        if device is None or device.status not in {
            "registered", "registered_awaiting_cloud_auth"
        }:
            raise HTTPException(403, "Device not registered")

        # Reject and burn invalid proofs, never return printer IPs before auth.
        challenge.state = "rejected"
        try:
            key = Ed25519PublicKey.from_public_bytes(
                decode_b64(device.public_key_b64, 32)
            )
            key.verify(
                decode_b64(request.signature_b64, 64),
                fetch_message(
                    challenge.challenge_id, device.hardware_id,
                    challenge.nonce_b64,
                ),
            )
        except (InvalidSignature, ValueError, UnicodeError):
            db.commit()
            raise HTTPException(403, "Invalid configuration fetch signature")

        row = db.get(PiTargetConfiguration, device.hardware_id)
        # A first-time Pi has no staged targets; do not infer or scan any.
        import json
        response = {
            "hardware_id": device.hardware_id,
            "version": row.version if row else 0,
            "printers": json.loads(row.targets_json) if row else [],
            "configuration_applied": False,
        }
        challenge.state = "verified_config_fetch"
        db.commit()
        return response
