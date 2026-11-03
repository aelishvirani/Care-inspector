"""Cloud key authentication foundation: no tokens, no elevated collector access.

Registration is Technician-authorized beforehand. A successful exchange
confirms current possession of its private key, but does not yet provide
API sessions, collector credentials, WebSockets or printer control access.
"""
import base64
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from .database import SessionLocal
from .pi_cloud_challenges import PiCloudChallenge
from .pi_cloud_crypto import verify_cloud_signature
from .pi_registered_devices import PiRegisteredDevice
from .pi_heartbeat import PiHeartbeat
from .auth import get_current_user, require_technician
from .models import User
from fastapi import Depends

router = APIRouter(prefix="/api/pi-auth", tags=["pi-cloud-auth"])


class ChallengeRequest(BaseModel):
    hardware_id: str = Field(min_length=8, max_length=128)


class ProofRequest(BaseModel):
    challenge_id: str = Field(min_length=36, max_length=36)
    hardware_id: str = Field(min_length=8, max_length=128)
    signature_b64: str = Field(min_length=88, max_length=88)


def utc(value):
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


@router.post("/challenge", status_code=201)
def start_cloud_auth(request: ChallengeRequest):
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        device = db.get(PiRegisteredDevice, request.hardware_id)
        # Generic error prevents enumeration of registered hardware IDs.
        if device is None or device.status not in {
            "registered_awaiting_cloud_auth", "registered"
        }:
            raise HTTPException(404, "Device unavailable")
        count = db.scalar(
            select(func.count()).select_from(PiCloudChallenge).where(
                PiCloudChallenge.hardware_id == request.hardware_id,
                PiCloudChallenge.state == "pending",
                PiCloudChallenge.expires_at > now,
            )
        )
        if count >= 3:
            raise HTTPException(429, "Too many active challenges")
        challenge_id = str(uuid4())
        nonce = base64.b64encode(secrets.token_bytes(32)).decode("ascii")
        db.add(PiCloudChallenge(
            challenge_id=challenge_id, hardware_id=device.hardware_id,
            nonce_b64=nonce, state="pending", created_at=now,
            expires_at=now + timedelta(seconds=60),
        ))
        db.commit()
    return {"challenge_id": challenge_id, "nonce_b64": nonce, "expires_in_seconds": 60}


@router.post("/prove")
def prove_cloud_identity(request: ProofRequest):
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        challenge = db.get(PiCloudChallenge, request.challenge_id)
        if challenge is None or challenge.hardware_id != request.hardware_id:
            raise HTTPException(404, "Challenge not found")
        if utc(challenge.expires_at) <= now:
            challenge.state = "expired"
            db.commit()
            raise HTTPException(410, "Challenge expired")
        if challenge.state != "pending":
            raise HTTPException(409, "Challenge already used")
        device = db.get(PiRegisteredDevice, challenge.hardware_id)
        if device is None or device.status not in {
            "registered_awaiting_cloud_auth", "registered"
        }:
            raise HTTPException(403, "Device not authorized")
        # Consume the challenge even when signature verification fails.
        challenge.state = "rejected"
        try:
            valid = verify_cloud_signature(
                device.public_key_b64, challenge.challenge_id,
                device.hardware_id, challenge.nonce_b64, request.signature_b64,
            )
        except ValueError:
            valid = False
        if valid:
            challenge.state = "verified"
            heartbeat = db.get(PiHeartbeat, device.hardware_id)
            if heartbeat is None:
                heartbeat = PiHeartbeat(hardware_id=device.hardware_id, last_authenticated_at=now)
                db.add(heartbeat)
            else:
                heartbeat.last_authenticated_at = now
        db.commit()
        if not valid:
            raise HTTPException(403, "Invalid signature")
        return {
            "hardware_id": device.hardware_id,
            "authenticated": True,
            "cloud_session_issued": False,
            "collector_access_granted": False,
        }


@router.get("/devices")
def registered_pi_presence(user: User = Depends(get_current_user)):
    """Technician/Admin-only Pi last-authenticated timestamps.

    Online is a recent signed check-in, not a persistent network connection.
    """
    require_technician(user)
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        rows = db.execute(
            select(PiRegisteredDevice, PiHeartbeat)
            .outerjoin(PiHeartbeat, PiHeartbeat.hardware_id == PiRegisteredDevice.hardware_id)
        ).all()
        return [
            {
                "hardware_id": device.hardware_id,
                "status": device.status,
                "last_authenticated_at": (
                    utc(hb.last_authenticated_at).isoformat() if hb else None
                ),
                "recently_authenticated": bool(
                    hb and (now - utc(hb.last_authenticated_at)).total_seconds() <= 180
                ),
            }
            for device, hb in rows
        ]
