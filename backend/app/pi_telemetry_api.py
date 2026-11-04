"""Isolated, signed read-only Pi measurement ingestion.

Not used by the legacy simulator WebSocket. A Pi can report only its already
discovered, customer-assigned printer. This API never grants printer commands.
"""
import hashlib
import json
import math
from datetime import datetime, timezone

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from .alerts import evaluate_measurement, set_alert
from .database import SessionLocal
from .models import Configuration, Device, Measurement
from .pi_cloud_challenges import PiCloudChallenge
from .pi_cloud_crypto import cloud_message
from .pi_pairing_crypto import decode_b64
from .pi_registered_devices import PiRegisteredDevice
from .pi_signed_discovery import collector_id_for_pi
from .printer_discovery_links import PrinterDiscoveryLink

router = APIRouter(prefix="/api/pi-telemetry", tags=["pi-telemetry"])
DOMAIN = b"care-inspector-pi-telemetry-v1\x00"


class PiMeasurement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    device_id: str = Field(min_length=3, max_length=100)
    timestamp: datetime
    status: str = Field(min_length=1, max_length=80)
    print_count: int | None = Field(default=None, ge=0)
    temperature_c: float = Field(ge=-100, le=200)
    pressure_mpa: float = Field(ge=0, le=10)
    ink_level_percent: int | None = Field(default=None, ge=0, le=100)
    makeup_level_percent: int | None = Field(default=None, ge=0, le=100)


class SignedPiMeasurement(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    hardware_id: str = Field(min_length=8, max_length=128)
    challenge_id: str = Field(min_length=36, max_length=36)
    signature_b64: str = Field(min_length=88, max_length=88)
    measurement: PiMeasurement


def telemetry_message(challenge_id: str, hardware_id: str,
                      nonce_b64: str, measurement: PiMeasurement) -> bytes:
    encoded = json.dumps(
        measurement.model_dump(mode="json"),
        sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    ).encode("ascii")
    return (DOMAIN + cloud_message(challenge_id, hardware_id, nonce_b64) +
            b"\x00" + hashlib.sha256(encoded).digest())


def aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


@router.post("/ingest")
def ingest_signed_telemetry(request: SignedPiMeasurement):
    with SessionLocal() as db:
        challenge = db.get(PiCloudChallenge, request.challenge_id)
        if challenge is None or challenge.hardware_id != request.hardware_id:
            raise HTTPException(404, "Challenge unavailable")
        if challenge.state != "pending":
            raise HTTPException(409, "Challenge already used")
        now = datetime.now(timezone.utc)
        if aware(challenge.expires_at) <= now:
            challenge.state = "expired"
            db.commit()
            raise HTTPException(410, "Challenge expired")

        pi = db.get(PiRegisteredDevice, request.hardware_id)
        if pi is None or pi.status not in {"registered", "registered_awaiting_cloud_auth"}:
            raise HTTPException(403, "Pi registration unavailable")

        # Consume the challenge even for a bad signature, preventing replay.
        challenge.state = "rejected"
        try:
            key = Ed25519PublicKey.from_public_bytes(decode_b64(pi.public_key_b64, 32))
            key.verify(
                decode_b64(request.signature_b64, 64),
                telemetry_message(challenge.challenge_id, request.hardware_id,
                                  challenge.nonce_b64, request.measurement),
            )
        except (ValueError, UnicodeError, InvalidSignature):
            db.commit()
            raise HTTPException(403, "Invalid telemetry signature")

        measurement = request.measurement
        timestamp = aware(measurement.timestamp)
        if abs((now - timestamp).total_seconds()) > 120:
            db.commit()
            raise HTTPException(422, "Measurement timestamp outside allowed window")
        if not all(math.isfinite(n) for n in (
            measurement.temperature_c, measurement.pressure_mpa
        )):
            db.commit()
            raise HTTPException(422, "Non-finite measurements are not permitted")

        link = db.get(PrinterDiscoveryLink, measurement.device_id)
        device = db.get(Device, measurement.device_id)
        if (link is None or
            link.collector_id != collector_id_for_pi(pi.hardware_id) or
            device is None or device.customer_id is None):
            db.commit()
            raise HTTPException(403, "Printer not linked and assigned to this Pi")

        # Never overwrite a newer reading, even if the signed request is valid.
        if device.last_seen is not None and timestamp <= aware(device.last_seen):
            db.commit()
            raise HTTPException(409, "Measurement is not newer than existing data")

        data = measurement.model_dump(mode="python")
        data.update(source="hitachi_modbus", online=True, timestamp=timestamp)
        db.add(Measurement(**data))
        device.source = "hitachi_modbus"
        device.online = True
        device.status = measurement.status
        device.last_seen = timestamp
        device.print_count = measurement.print_count
        device.temperature_c = measurement.temperature_c
        device.pressure_mpa = measurement.pressure_mpa
        device.ink_level_percent = measurement.ink_level_percent
        device.makeup_level_percent = measurement.makeup_level_percent

        set_alert(
            db, device_id=device.device_id, alert_type="offline",
            severity="critical", message="Device offline", active=False,
        )
        config = db.get(Configuration, 1)
        if config is not None:
            evaluate_measurement(db, data, config)
        challenge.state = "telemetry_stored"
        db.commit()
        return {
            "status": "stored", "device_id": device.device_id,
            "timestamp": timestamp.isoformat(), "controls_enabled": False,
        }
