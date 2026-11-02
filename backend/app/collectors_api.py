"""Management and authenticated read-only enrollment for Pi collectors.

This route does not start hardware drivers, enable connections, or issue commands.
"""
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from .audit import log_audit
from .auth import get_current_user, require_technician
from .collectors import RegisteredCollector
from .database import SessionLocal
from .models import Customer, User, Device
from .printer_connections import PrinterConnection

router = APIRouter(tags=["collectors"])

ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")


class CollectorCreate(BaseModel):
    collector_id: str = Field(min_length=3, max_length=64)
    name: str = Field(min_length=1, max_length=100)
    customer_id: int | None = None


def public_payload(row: RegisteredCollector) -> dict:
    return {
        "collector_id": row.collector_id,
        "name": row.name,
        "customer_id": row.customer_id,
        "enabled": row.enabled,
        "last_seen": row.last_seen.isoformat() if row.last_seen else None,
    }


@router.get("/api/secure/management/collectors")
def list_collectors(user: User = Depends(get_current_user)):
    require_technician(user)
    with SessionLocal() as db:
        return [
            public_payload(row)
            for row in db.scalars(
                select(RegisteredCollector).order_by(RegisteredCollector.name)
            ).all()
        ]


@router.post("/api/secure/management/collectors", status_code=201)
def register_collector(
    request: CollectorCreate,
    user: User = Depends(get_current_user),
):
    require_technician(user)
    collector_id = request.collector_id.strip().lower()
    name = request.name.strip()
    if not ID_RE.fullmatch(collector_id):
        raise HTTPException(400, "Collector ID must be 3-64 lowercase letters, numbers, _ or -")
    if not name:
        raise HTTPException(400, "Collector name is required")
    with SessionLocal() as db:
        if db.get(RegisteredCollector, collector_id):
            raise HTTPException(409, "Collector ID already registered")
        if request.customer_id is not None and db.get(Customer, request.customer_id) is None:
            raise HTTPException(404, "Customer not found")
        secret = secrets.token_urlsafe(48)
        row = RegisteredCollector(
            collector_id=collector_id,
            name=name,
            customer_id=request.customer_id,
            token_hash=hashlib.sha256(secret.encode()).hexdigest(),
            enabled=True,
        )
        db.add(row)
        log_audit(
            db, user=user, category="MANAGEMENT",
            action="COLLECTOR_REGISTERED", object_type="collector",
            object_id=collector_id, details="Registered collector identity; not connected",
        )
        db.commit()
        return {
            **public_payload(row),
            "enrollment_token": secret,
            "message": "Store this token securely on the Raspberry Pi. It is shown only once.",
        }


def authenticate_collector(
    collector_id: str | None,
    collector_token: str | None,
    db,
) -> RegisteredCollector:
    if not collector_id or not collector_token:
        raise HTTPException(401, "Collector credentials required")
    row = db.get(RegisteredCollector, collector_id)
    if row is None or not row.enabled:
        raise HTTPException(401, "Invalid collector credentials")
    supplied = hashlib.sha256(collector_token.encode()).hexdigest()
    if not hmac.compare_digest(row.token_hash, supplied):
        raise HTTPException(401, "Invalid collector credentials")
    return row


@router.post("/api/collector/heartbeat")
def collector_heartbeat(
    x_collector_id: str | None = Header(default=None),
    x_collector_token: str | None = Header(default=None),
):
    with SessionLocal() as db:
        row = authenticate_collector(x_collector_id, x_collector_token, db)
        row.last_seen = datetime.now(timezone.utc)
        db.commit()
        return {"collector_id": row.collector_id, "authenticated": True}


@router.get("/api/collector/assigned-printers")
def collector_assigned_printers(
    x_collector_id: str | None = Header(default=None),
    x_collector_token: str | None = Header(default=None),
):
    """Inventory metadata only; never returns IPs or enables printer control."""
    with SessionLocal() as db:
        row = authenticate_collector(x_collector_id, x_collector_token, db)
        connections = db.scalars(
            select(PrinterConnection).where(
                PrinterConnection.collector_id == row.collector_id
            )
        ).all()
        printers = []
        for connection in connections:
            device = db.get(Device, connection.device_id)
            if device is None:
                continue
            if row.customer_id is not None and device.customer_id != row.customer_id:
                continue
            printers.append({
                "device_id": device.device_id,
                "display_name": device.display_name,
                "manufacturer": connection.manufacturer,
                "protocol": connection.protocol,
                "monitoring_enabled": False,
            })
        return {"collector_id": row.collector_id, "printers": printers}


class PrinterAnnouncement(BaseModel):
    """Information detected by an authenticated Pi, never by an anonymous MAC."""
    device_id: str = Field(min_length=3, max_length=100)
    display_name: str | None = Field(default=None, max_length=100)
    manufacturer: str | None = Field(default=None, max_length=100)
    model_name: str | None = Field(default=None, max_length=100)


class DiscoveryAnnouncement(BaseModel):
    mac_address: str
    printers: list[PrinterAnnouncement] = Field(default_factory=list, max_length=30)


MAC_RE = re.compile(r"^(?:[0-9a-f]{2}:){5}[0-9a-f]{2}$")
DEVICE_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]{2,99}$")


@router.post("/api/collector/discover")
def announce_discovered_printers(
    request: DiscoveryAnnouncement,
    x_collector_id: str | None = Header(default=None),
    x_collector_token: str | None = Header(default=None),
):
    """Autocreate *unassigned* inventory from an already enrolled collector.

    This endpoint cannot enable a connection or send commands. The MAC is
    informative only, not a credential. Future Pi agent performs local probing.
    """
    mac = request.mac_address.strip().lower().replace("-", ":")
    if not MAC_RE.fullmatch(mac):
        raise HTTPException(400, "Invalid network MAC address")
    ids = [p.device_id for p in request.printers]
    if len(ids) != len(set(ids)) or any(not DEVICE_RE.fullmatch(x) for x in ids):
        raise HTTPException(400, "Invalid or duplicate printer device IDs")

    with SessionLocal() as db:
        collector = authenticate_collector(x_collector_id, x_collector_token, db)
        collector.last_seen = datetime.now(timezone.utc)
        discovered = []
        for info in request.printers:
            existing = db.get(Device, info.device_id)
            if existing is not None:
                # Never claim an existing printer for another collector.
                connection = db.get(PrinterConnection, info.device_id)
                if connection is None or connection.collector_id != collector.collector_id:
                    discovered.append({"device_id": info.device_id, "status": "already_exists"})
                    continue
                discovered.append({"device_id": info.device_id, "status": "known"})
                continue

            # Untrusted discovery cannot set a customer, go online, or become controllable.
            db.add(Device(
                device_id=info.device_id,
                display_name=info.display_name or info.device_id,
                customer_id=None,
                model_name=info.model_name,
                source="discovered",
                online=False,
                status="pending_assignment",
                last_seen=collector.last_seen,
                temperature_c=0,
                pressure_mpa=0,
            ))
            discovered.append({"device_id": info.device_id, "status": "unassigned"})
        db.commit()
        return {
            "collector_id": collector.collector_id,
            "mac_address": mac,
            "printers": discovered,
            "controls_enabled": False,
        }
