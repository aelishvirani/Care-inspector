"""Technician-controlled staging of Pi printer target configuration.

This is server-side staging only. The Pi cannot yet fetch/apply it.
No network scans, device writes, or changes to working collector settings.
"""
import ipaddress
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.exc import IntegrityError

from .audit import log_audit
from .auth import get_current_user, require_technician
from .database import SessionLocal
from .models import User
from .pi_registered_devices import PiRegisteredDevice
from .pi_target_config import PiTargetConfiguration

router = APIRouter(
    prefix="/api/secure/management/pi-targets", tags=["pi-target-config"]
)


class PrinterTargetInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    host: str = Field(min_length=3, max_length=45)
    port: int = Field(ge=1, le=65535)
    protocol: str
    manufacturer: str
    device_id: str = Field(default="", max_length=100)


class SaveTargets(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    expected_version: int = Field(ge=0)
    printers: list[PrinterTargetInput] = Field(max_length=1)


def normalized_targets(printers: list[PrinterTargetInput]) -> list[dict]:
    import re
    result = []
    used = set()
    for printer in printers:
        try:
            address = ipaddress.ip_address(printer.host)
        except ValueError as exc:
            raise HTTPException(422, "Configured printer host must be an IP literal") from exc
        if not (address.is_private or address.is_loopback or address.is_link_local):
            raise HTTPException(422, "Printer IP must be local/private")
        if printer.protocol != "modbus" or printer.manufacturer != "Hitachi":
            raise HTTPException(422, "Only Hitachi Modbus is supported in this version")
        if printer.device_id and not re.fullmatch(
            r"[a-zA-Z0-9][a-zA-Z0-9_.:-]{2,99}", printer.device_id
        ):
            raise HTTPException(422, "Invalid printer device ID")
        key = (str(address), printer.port)
        if key in used:
            raise HTTPException(422, "Duplicate printer endpoint")
        used.add(key)
        result.append({
            "host": str(address), "port": printer.port,
            "protocol": printer.protocol, "manufacturer": printer.manufacturer,
            "device_id": printer.device_id,
        })
    return result


@router.get("/{hardware_id}")
def get_pi_targets(hardware_id: str, user: User = Depends(get_current_user)):
    require_technician(user)
    with SessionLocal() as db:
        if db.get(PiRegisteredDevice, hardware_id) is None:
            raise HTTPException(404, "Registered Pi not found")
        row = db.get(PiTargetConfiguration, hardware_id)
        return {
            "hardware_id": hardware_id,
            "version": row.version if row else 0,
            "printers": json.loads(row.targets_json) if row else [],
            "applied_to_pi": False,
        }


@router.put("/{hardware_id}")
def save_pi_targets(
    hardware_id: str, request: SaveTargets,
    user: User = Depends(get_current_user),
):
    require_technician(user)
    targets = normalized_targets(request.printers)
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        if db.get(PiRegisteredDevice, hardware_id) is None:
            raise HTTPException(404, "Registered Pi not found")
        row = db.get(PiTargetConfiguration, hardware_id)
        version = row.version if row else 0
        if version != request.expected_version:
            raise HTTPException(409, "Pi configuration changed; reload before saving")
        if row is None:
            row = PiTargetConfiguration(
                hardware_id=hardware_id, version=1,
                targets_json=json.dumps(targets, separators=(",", ":")),
                updated_by_user_id=user.id, updated_at=now,
            )
            db.add(row)
        else:
            row.version += 1
            row.targets_json = json.dumps(targets, separators=(",", ":"))
            row.updated_by_user_id = user.id
            row.updated_at = now
        log_audit(
            db, user=user, category="MANAGEMENT", action="PI_TARGETS_STAGED",
            object_type="raspberry_pi", object_id=hardware_id,
            details=f"Staged target version {row.version}; not applied to Pi",
        )
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(409, "Concurrent configuration update") from exc
        return {
            "hardware_id": hardware_id,
            "version": row.version,
            "printers": targets,
            "applied_to_pi": False,
        }
