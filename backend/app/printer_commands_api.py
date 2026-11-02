import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from .audit import log_audit
from .auth import get_current_user, require_technician
from .database import SessionLocal
from .models import Device, User
from .printer_commands import PrinterCommand

router = APIRouter(
    prefix="/api/secure/management/devices",
    tags=["printer-commands"],
)

HEX_PATTERN = re.compile(r"^[0-9A-Fa-f]+$")


class CommandCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    hex_code: str = Field(min_length=2, max_length=512)


def serialize(command: PrinterCommand) -> dict:
    return {
        "id": command.id,
        "device_id": command.device_id,
        "name": command.name,
        "hex_code": command.hex_code,
    }


def verify_device(db, device_id: str):
    if db.get(Device, device_id) is None:
        raise HTTPException(status_code=404, detail="Printer not found")


@router.get("/{device_id}/commands")
def list_printer_commands(
    device_id: str,
    user: User = Depends(get_current_user),
):
    require_technician(user)
    with SessionLocal() as db:
        verify_device(db, device_id)
        commands = db.scalars(
            select(PrinterCommand)
            .where(PrinterCommand.device_id == device_id)
            .order_by(PrinterCommand.name, PrinterCommand.id)
        ).all()
        return [serialize(command) for command in commands]


@router.post("/{device_id}/commands", status_code=201)
def add_printer_command(
    device_id: str,
    payload: CommandCreate,
    user: User = Depends(get_current_user),
):
    require_technician(user)
    name = payload.name.strip()
    cleaned_hex = re.sub(r"\\s+", "", payload.hex_code).upper()
    if not name:
        raise HTTPException(status_code=400, detail="Command name is required")
    if len(cleaned_hex) % 2 or not HEX_PATTERN.fullmatch(cleaned_hex):
        raise HTTPException(
            status_code=400,
            detail="Hex code must contain complete bytes (0-9, A-F)",
        )
    with SessionLocal() as db:
        verify_device(db, device_id)
        existing = db.scalar(
            select(PrinterCommand).where(
                PrinterCommand.device_id == device_id,
                PrinterCommand.name == name,
            )
        )
        if existing:
            raise HTTPException(status_code=409, detail="Command name already exists")
        command = PrinterCommand(
            device_id=device_id,
            name=name,
            hex_code=cleaned_hex,
        )
        db.add(command)
        db.flush()
        log_audit(
            db, user=user, category="MANAGEMENT",
            action="PRINTER_COMMAND_CREATED", object_type="printer_command",
            object_id=command.id, details=f"Command configured for {device_id}",
        )
        db.commit()
        db.refresh(command)
        return serialize(command)


@router.delete("/{device_id}/commands/{command_id}")
def remove_printer_command(
    device_id: str,
    command_id: int,
    user: User = Depends(get_current_user),
):
    require_technician(user)
    with SessionLocal() as db:
        verify_device(db, device_id)
        command = db.get(PrinterCommand, command_id)
        if command is None or command.device_id != device_id:
            raise HTTPException(status_code=404, detail="Command not found")
        db.delete(command)
        log_audit(
            db, user=user, category="MANAGEMENT",
            action="PRINTER_COMMAND_DELETED", object_type="printer_command",
            object_id=command_id, details=f"Command removed from {device_id}",
        )
        db.commit()
        return {"deleted": True}


# No POST execution endpoint on purpose. Stored hex is not sent to hardware.
