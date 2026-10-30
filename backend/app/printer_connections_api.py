import ipaddress
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError

from .auth import get_current_user, require_technician
from .audit import log_audit
from .database import SessionLocal
from .models import Device, User
from .printer_connections import PrinterConnection


router = APIRouter(
    prefix="/api/secure/management/devices",
    tags=["printer-connections"],
)


class PrinterConnectionUpdate(BaseModel):
    manufacturer: Literal["hitachi"]
    protocol: Literal["modbus_tcp"]
    host: str
    port: int = Field(ge=1, le=65535)
    unit_id: int = Field(ge=1, le=247)
    collector_id: str | None = None
    enabled: bool = False


def connection_payload(connection):
    return {
        "device_id": connection.device_id,
        "manufacturer": connection.manufacturer,
        "protocol": connection.protocol,
        "host": connection.host,
        "port": connection.port,
        "unit_id": connection.unit_id,
        "collector_id": connection.collector_id,
        "enabled": connection.enabled,
    }


@router.get("/{device_id}/connection")
def get_printer_connection(
    device_id: str,
    user: User = Depends(get_current_user),
):
    require_technician(user)

    with SessionLocal() as db:
        if db.get(Device, device_id) is None:
            raise HTTPException(404, "Printer not found")

        connection = db.get(PrinterConnection, device_id)

        if connection is None:
            return {
                "device_id": device_id,
                "configured": False,
            }

        return {
            **connection_payload(connection),
            "configured": True,
        }


@router.put("/{device_id}/connection")
def save_printer_connection(
    device_id: str,
    data: PrinterConnectionUpdate,
    user: User = Depends(get_current_user),
):
    require_technician(user)

    try:
        ipaddress.ip_address(data.host.strip())
    except ValueError:
        raise HTTPException(
            400,
            "A valid printer IP address is required",
        )

    # Provisioning is not implemented yet. Prevent settings
    # from being represented as active connections.
    if data.enabled:
        raise HTTPException(
            400,
            "Monitoring activation is not implemented yet",
        )

    with SessionLocal() as db:
        device = db.get(Device, device_id)

        if device is None:
            raise HTTPException(404, "Printer not found")

        connection = db.get(PrinterConnection, device_id)
        created = connection is None

        if created:
            connection = PrinterConnection(device_id=device_id)
            db.add(connection)

        connection.manufacturer = data.manufacturer
        connection.protocol = data.protocol
        connection.host = data.host.strip()
        connection.port = data.port
        connection.unit_id = data.unit_id
        connection.collector_id = (
            data.collector_id.strip()
            if data.collector_id
            else None
        )
        connection.enabled = False

        log_audit(
            db,
            user=user,
            category="MANAGEMENT",
            action=(
                "PRINTER_CONNECTION_CREATED"
                if created
                else "PRINTER_CONNECTION_UPDATED"
            ),
            object_type="device",
            object_id=device_id,
            details="Printer connection settings saved",
        )

        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                409,
                "Connection settings could not be saved",
            )

        db.refresh(connection)

        return {
            **connection_payload(connection),
            "configured": True,
        }
