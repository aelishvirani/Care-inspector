"""Single-use signed printer inventory announcements from registered Pis.

A signature binds the specific normalized inventory payload to a fresh server
challenge. This cannot grant printer commands or collector API bearer tokens.
"""
import base64
import hashlib
import json
from datetime import datetime, timezone

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .collectors import RegisteredCollector
from .collectors_api import DiscoveryAnnouncement, record_discovered_printers
from .database import SessionLocal
from .pi_cloud_challenges import PiCloudChallenge
from .pi_pairing_crypto import decode_b64
from .pi_registered_devices import PiRegisteredDevice

router = APIRouter(prefix="/api/pi-discovery", tags=["pi-signed-discovery"])
DOMAIN = b"care-inspector-pi-signed-discovery-v1\x00"


class SignedDiscovery(BaseModel):
    hardware_id: str = Field(min_length=8, max_length=128)
    challenge_id: str = Field(min_length=36, max_length=36)
    signature_b64: str = Field(min_length=88, max_length=88)
    announcement: DiscoveryAnnouncement


def canonical_announcement(announcement: DiscoveryAnnouncement) -> bytes:
    # Use Pydantic's normalized schema and stable field ordering on both ends.
    # JSON ensure_ascii and separators must match the Pi client exactly.
    return json.dumps(
        announcement.model_dump(mode="json"),
        sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("ascii")


def discovery_message(challenge_id: str, hardware_id: str,
                      nonce_b64: str, announcement: DiscoveryAnnouncement) -> bytes:
    from .pi_cloud_crypto import cloud_message
    # cloud_message validates challenge, identity and nonce encodings.
    binding = cloud_message(challenge_id, hardware_id, nonce_b64)
    digest = hashlib.sha256(canonical_announcement(announcement)).digest()
    return DOMAIN + binding + b"\x00" + digest


def collector_id_for_pi(hardware_id: str) -> str:
    # Stable, unique mapping into 64-character collector ID constraints.
    return "pi_" + hashlib.sha256(hardware_id.encode("ascii")).hexdigest()[:40]


@router.post("/announce")
def signed_discovery(request: SignedDiscovery):
    with SessionLocal() as db:
        challenge = db.get(PiCloudChallenge, request.challenge_id)
        if challenge is None or challenge.hardware_id != request.hardware_id:
            raise HTTPException(404, "Challenge unavailable")
        if challenge.state != "pending":
            raise HTTPException(409, "Challenge already used")
        expiry = challenge.expires_at
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) >= expiry:
            challenge.state = "expired"
            db.commit()
            raise HTTPException(410, "Challenge expired")
        pi = db.get(PiRegisteredDevice, request.hardware_id)
        if pi is None or pi.status not in {"registered", "registered_awaiting_cloud_auth"}:
            raise HTTPException(403, "Pi registration unavailable")

        # Burn the challenge even after an invalid signature.
        challenge.state = "rejected"
        try:
            public_key = Ed25519PublicKey.from_public_bytes(
                decode_b64(pi.public_key_b64, 32)
            )
            public_key.verify(
                decode_b64(request.signature_b64, 64),
                discovery_message(challenge.challenge_id, request.hardware_id,
                                  challenge.nonce_b64, request.announcement),
            )
        except (InvalidSignature, ValueError, UnicodeError):
            db.commit()
            raise HTTPException(403, "Invalid discovery signature")

        # Bound to the authenticated Pi identity, not user-supplied collector ID.
        collector_id = collector_id_for_pi(pi.hardware_id)
        collector = db.get(RegisteredCollector, collector_id)
        if collector is None:
            # No bearer credential is issued or accessible by the Pi through
            # this route. Preserve old token-based clients independently.
            collector = RegisteredCollector(
                collector_id=collector_id,
                name="Raspberry Pi " + pi.hardware_id[-12:],
                customer_id=None,
                token_hash=hashlib.sha256(
                    ("no-bearer-token:" + pi.hardware_id).encode()
                ).hexdigest(),
                enabled=False,
            )
            db.add(collector)
        elif collector.enabled:
            # Never silently take over a manually managed collector identity.
            db.rollback()
            raise HTTPException(409, "Collector identity conflict")

        # Strict Pi-only 1:1 mapping. Legacy token collectors remain unchanged.
        # Preserve existing assignments and never silently replace a printer.
        if len(request.announcement.printers) > 1:
            challenge.state = "rejected"
            db.commit()
            raise HTTPException(409, "One Raspberry Pi can report only one printer")
        from .printer_discovery_links import PrinterDiscoveryLink
        existing_printer_ids = set(db.scalars(
            select(PrinterDiscoveryLink.device_id).where(
                PrinterDiscoveryLink.collector_id == collector_id
            )
        ).all())
        incoming_ids = {p.device_id for p in request.announcement.printers}
        if existing_printer_ids and incoming_ids and incoming_ids != existing_printer_ids:
            challenge.state = "rejected"
            db.commit()
            raise HTTPException(
                409, "Pi already has a linked printer; explicit reassignment required"
            )
        if len(existing_printer_ids) > 1:
            challenge.state = "rejected"
            db.commit()
            raise HTTPException(409, "Legacy Pi has multiple printer links; manual resolution required")

        result = record_discovered_printers(db, collector, request.announcement)
        challenge.state = "verified_discovery"
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(409, "Conflicting discovered inventory") from exc
        return {**result, "authenticated_pi": True}
