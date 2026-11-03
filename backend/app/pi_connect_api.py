"""Explicit technician-authorized Pi key registration.

No token issuance or collector activation. The Pi must later authenticate
through a cryptographic cloud credential provisioning flow. A key proof
alone cannot establish manufacturer/device ownership; the authorized
technician's explicit Connect action is a trust-on-first-use decision.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

from .audit import log_audit
from .auth import get_current_user, require_technician
from .database import SessionLocal
from .models import User
from .pi_pairing import PiPairingAttempt
from .pi_registered_devices import PiRegisteredDevice

router = APIRouter(
    prefix="/api/secure/management/pi-connect", tags=["pi-connect"]
)


class ConnectPiRequest(BaseModel):
    pairing_id: str = Field(min_length=36, max_length=36)
    authorize_device: bool = Field(
        description="Explicit technician approval of the locally selected BLE device"
    )


def public_device(record: PiRegisteredDevice) -> dict:
    return {
        "hardware_id": record.hardware_id,
        "status": record.status,
        "registered_at": record.registered_at,
        "authorized_by_user_id": record.authorized_by_user_id,
        "cloud_connected": False,
    }


@router.post("", status_code=201)
def connect_pi(
    request: ConnectPiRequest,
    user: User = Depends(get_current_user),
):
    require_technician(user)
    if request.authorize_device is not True:
        raise HTTPException(400, "Explicit Connect authorization required")
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        pair = db.get(PiPairingAttempt, request.pairing_id)
        if pair is None or pair.actor_user_id != user.id:
            raise HTTPException(404, "Pairing attempt not found")
        if pair.status != "proof_validated":
            raise HTTPException(409, "Device key proof must succeed before Connect")

        # Restrict enrollment to the original short-lived pairing window.
        expiry = pair.expires_at
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if now >= expiry:
            raise HTTPException(410, "Verified pairing has expired; verify the key again")

        if db.get(PiRegisteredDevice, pair.hardware_id) is not None:
            raise HTTPException(409, "Raspberry Pi hardware ID is already registered")
        if db.scalar(select(PiRegisteredDevice.hardware_id).where(
            PiRegisteredDevice.public_key_b64 == pair.public_key_b64
        )) is not None:
            raise HTTPException(409, "Raspberry Pi public key is already registered")

        record = PiRegisteredDevice(
            hardware_id=pair.hardware_id,
            public_key_b64=pair.public_key_b64,
            pairing_id=pair.pairing_id,
            authorized_by_user_id=user.id,
            registered_at=now,
            status="registered_awaiting_cloud_auth",
        )
        db.add(record)
        pair.status = "registered"
        log_audit(
            db, user=user, category="MANAGEMENT",
            action="PI_KEY_REGISTERED", object_type="raspberry_pi",
            object_id=pair.hardware_id,
            details="Explicit technician-approved key registration; cloud authentication pending",
        )
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(409, "Raspberry Pi is already registered") from exc
        return public_device(record)


@router.get("")
def list_connected_pi_keys(user: User = Depends(get_current_user)):
    require_technician(user)
    with SessionLocal() as db:
        rows = db.scalars(
            select(PiRegisteredDevice).order_by(PiRegisteredDevice.registered_at.desc())
        ).all()
        return [public_device(row) for row in rows]
