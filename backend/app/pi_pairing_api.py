"""Technician-controlled BLE key possession challenges (no cloud enrollment).

Start and verify are deliberately NOT a complete secure pairing mechanism.
Verifying a key does not attest which physical Pi owns that key.
"""
import base64
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .auth import get_current_user, require_technician
from .database import SessionLocal
from .models import User
from .pi_pairing import PiPairingAttempt
from .pi_pairing_crypto import (
    HARDWARE_ID_RE, decode_b64, verify_pi_proof,
)

router = APIRouter(prefix="/api/secure/management/pi-pairing", tags=["pi-pairing"])


class StartPairing(BaseModel):
    hardware_id: str = Field(min_length=8, max_length=128)
    public_key_b64: str = Field(min_length=40, max_length=64)


class VerifyPairing(BaseModel):
    signature_b64: str = Field(min_length=80, max_length=100)


@router.post("/start", status_code=201)
def start_pairing(request: StartPairing, user: User = Depends(get_current_user)):
    require_technician(user)
    if not HARDWARE_ID_RE.fullmatch(request.hardware_id):
        raise HTTPException(400, "Invalid hardware identifier")
    try:
        decode_b64(request.public_key_b64, 32)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    now = datetime.now(timezone.utc)
    pairing_id = str(uuid4())
    challenge = base64.b64encode(secrets.token_bytes(32)).decode("ascii")
    with SessionLocal() as db:
        # Preserve pairing history referenced by permanent Pi registrations.
        # Expired attempts do not count against the pending limit.
        from sqlalchemy import func, select
        pending_count = db.scalar(
            select(func.count()).select_from(PiPairingAttempt).where(
                PiPairingAttempt.actor_user_id == user.id,
                PiPairingAttempt.status == "pending",
                PiPairingAttempt.expires_at > now,
            )
        )
        if pending_count >= 5:
            db.rollback()
            raise HTTPException(429, "Too many pending pairing attempts")
        db.add(PiPairingAttempt(
            pairing_id=pairing_id,
            actor_user_id=user.id,
            hardware_id=request.hardware_id,
            public_key_b64=request.public_key_b64,
            challenge_b64=challenge,
            created_at=now,
            expires_at=now + timedelta(minutes=3),
            status="pending",
        ))
        db.commit()
    return {
        "pairing_id": pairing_id,
        "challenge_b64": challenge,
        "expires_in_seconds": 180,
        "status": "awaiting_key_proof",
        "enrolled": False,
    }


@router.post("/{pairing_id}/verify")
def verify_pairing(
    pairing_id: str,
    request: VerifyPairing,
    user: User = Depends(get_current_user),
):
    require_technician(user)
    with SessionLocal() as db:
        attempt = db.get(PiPairingAttempt, pairing_id)
        if attempt is None or attempt.actor_user_id != user.id:
            raise HTTPException(404, "Pairing attempt not found")
        # SQLite can return naive datetime despite timezone=True.
        expiry = attempt.expires_at
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) >= expiry:
            attempt.status = "expired"
            db.commit()
            raise HTTPException(410, "Pairing challenge expired")
        if attempt.status != "pending":
            raise HTTPException(409, "Pairing challenge is no longer pending")
        try:
            valid = verify_pi_proof(
                attempt.public_key_b64, pairing_id, attempt.hardware_id,
                attempt.challenge_b64, request.signature_b64,
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        # One attempt only: consume even on invalid signature to prevent retries.
        attempt.status = "proof_validated" if valid else "proof_rejected"
        db.commit()
        if not valid:
            raise HTTPException(403, "Device key proof invalid")

        return {
            "pairing_id": pairing_id,
            "status": "key_possession_confirmed",
            "trusted_device": False,
            "enrolled": False,
            "next_step": "Requires independent physical ownership approval and secure enrollment",
        }
