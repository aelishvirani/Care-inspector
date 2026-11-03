"""Request intake and review queue for Pi enrollment (no activation).

Only verified key-possession can produce a pending request; no endpoint
approves a Pi or issues a cloud credential until independent ownership
verification is designed and tested.
"""
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .auth import get_current_user, require_technician
from .database import SessionLocal
from .models import User
from .pi_pairing import PiPairingAttempt
from .pi_enrollment import PiEnrollmentRequest


router = APIRouter(
    prefix="/api/secure/management/pi-enrollment",
    tags=["pi-enrollment"],
)


class CreateEnrollmentRequest(BaseModel):
    pairing_id: str = Field(min_length=36, max_length=36)


@router.post("/requests", status_code=201)
def create_enrollment_request(
    request: CreateEnrollmentRequest, user: User = Depends(get_current_user)
):
    require_technician(user)
    with SessionLocal() as db:
        pair = db.get(PiPairingAttempt, request.pairing_id)
        if pair is None or pair.actor_user_id != user.id:
            raise HTTPException(404, "Verified pairing attempt not found")
        if pair.status != "proof_validated":
            raise HTTPException(409, "Pairing key proof has not been validated")
        if db.scalar(select(PiEnrollmentRequest.enrollment_id).where(
            PiEnrollmentRequest.pairing_id == pair.pairing_id
        )) is not None:
            raise HTTPException(409, "Pairing has already been submitted for review")
        record = PiEnrollmentRequest(
            enrollment_id=str(uuid4()),
            pairing_id=pair.pairing_id,
            hardware_id=pair.hardware_id,
            public_key_b64=pair.public_key_b64,
            requested_by_user_id=user.id,
            status="pending_ownership_review",
            created_at=datetime.now(timezone.utc),
        )
        db.add(record)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            # Prevent duplicate or conflicting keys / hardware IDs.
            raise HTTPException(
                409, "Hardware identifier or public key already under enrollment review"
            ) from exc
        return {
            "enrollment_id": record.enrollment_id,
            "status": record.status,
            "trusted_device": False,
            "cloud_credentials_issued": False,
        }


@router.get("/requests")
def list_enrollment_requests(user: User = Depends(get_current_user)):
    require_technician(user)
    with SessionLocal() as db:
        records = db.scalars(
            select(PiEnrollmentRequest)
            .order_by(PiEnrollmentRequest.created_at.desc())
            .limit(100)
        ).all()
        return [
            {
                "enrollment_id": row.enrollment_id,
                "hardware_id": row.hardware_id,
                "status": row.status,
                "requested_by_user_id": row.requested_by_user_id,
                "created_at": row.created_at,
                "trusted_device": False,
            }
            for row in records
        ]
