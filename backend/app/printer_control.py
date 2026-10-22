from __future__ import annotations

import asyncio
from collections import defaultdict
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)

from .audit import (
    log_audit,
    write_audit_event,
)
from .auth import (
    get_current_user,
    require_technician,
)
from .database import SessionLocal
from .models import Device, User


router = APIRouter(
    tags=["printer-control"],
)

CONTROL_TIMEOUT_SECONDS = 20

_control_sockets: dict[
    str,
    WebSocket,
] = {}

_pending_commands: dict[
    str,
    asyncio.Future,
] = {}

_device_locks: defaultdict[
    str,
    asyncio.Lock,
] = defaultdict(asyncio.Lock)


def _running_state(status: str | None) -> bool:
    return status in {
        "ready",
        "printing",
        "starting",
        "drop_adjust",
        "ink_heating",
        "service",
    }


@router.websocket(
    "/ws/collector-control/{device_id}"
)
async def collector_control_websocket(
    websocket: WebSocket,
    device_id: str,
):
    await websocket.accept()

    previous = _control_sockets.get(
        device_id
    )

    if previous is not None:
        try:
            await previous.close()
        except Exception:
            pass

    _control_sockets[
        device_id
    ] = websocket

    write_audit_event(
        actor_email="SYSTEM",
        actor_role="SYSTEM",
        category="COLLECTOR_CONTROL",
        action="CONTROL_CHANNEL_CONNECTED",
        outcome="SUCCESS",
        object_type="device",
        object_id=device_id,
        ip_address=(
            websocket.client.host
            if websocket.client
            else None
        ),
    )

    try:
        while True:
            payload = (
                await websocket.receive_json()
            )

            if (
                payload.get("type")
                != "command_result"
            ):
                continue

            command_id = payload.get(
                "command_id"
            )

            future = (
                _pending_commands.get(
                    command_id
                )
            )

            if (
                future is not None
                and not future.done()
            ):
                future.set_result(
                    payload
                )

    except WebSocketDisconnect:
        pass

    except Exception as exc:
        write_audit_event(
            actor_email="SYSTEM",
            actor_role="SYSTEM",
            category="COLLECTOR_CONTROL",
            action="CONTROL_CHANNEL_ERROR",
            outcome="FAILURE",
            object_type="device",
            object_id=device_id,
            error_message=str(exc),
        )

    finally:
        if (
            _control_sockets.get(
                device_id
            )
            is websocket
        ):
            _control_sockets.pop(
                device_id,
                None,
            )

        write_audit_event(
            actor_email="SYSTEM",
            actor_role="SYSTEM",
            category="COLLECTOR_CONTROL",
            action="CONTROL_CHANNEL_DISCONNECTED",
            outcome="SUCCESS",
            object_type="device",
            object_id=device_id,
        )


@router.post(
    "/api/secure/devices/"
    "{device_id}/commands/{command}"
)
async def printer_command(
    device_id: str,
    command: str,
    request: Request,
    user: User = Depends(
        get_current_user
    ),
):
    require_technician(
        user
    )

    command = (
        command
        .strip()
        .lower()
    )

    if command not in {
        "start",
        "stop",
    }:
        raise HTTPException(
            status_code=400,
            detail=(
                "Supported commands are "
                "start and stop"
            ),
        )

    with SessionLocal() as db:
        device = db.get(
            Device,
            device_id,
        )

        if device is None:
            raise HTTPException(
                status_code=404,
                detail="Printer not found",
            )

        if not device.online:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Printer is offline and "
                    "cannot be controlled"
                ),
            )

        if (
            command == "start"
            and _running_state(
                device.status
            )
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Printer is already started"
                ),
            )

        if (
            command == "stop"
            and device.status
            == "stopped"
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Printer is already stopped"
                ),
            )

    websocket = (
        _control_sockets.get(
            device_id
        )
    )

    if websocket is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Printer collector control "
                "channel is not connected"
            ),
        )

    async with _device_locks[
        device_id
    ]:
        command_id = str(
            uuid4()
        )

        loop = (
            asyncio.get_running_loop()
        )

        future = (
            loop.create_future()
        )

        _pending_commands[
            command_id
        ] = future

        try:
            with SessionLocal() as db:
                log_audit(
                    db,
                    user=user,
                    action=(
                        "PRINTER_START_REQUESTED"
                        if command == "start"
                        else "PRINTER_STOP_REQUESTED"
                    ),
                    category="PRINTER_CONTROL",
                    outcome="SUCCESS",
                    object_type="device",
                    object_id=device_id,
                    details=(
                        f"Command {command} "
                        "sent to collector"
                    ),
                    request=request,
                )

                db.commit()

            await websocket.send_json(
                {
                    "type":
                        "printer_command",
                    "command_id":
                        command_id,
                    "device_id":
                        device_id,
                    "command":
                        command,
                }
            )

            result = await asyncio.wait_for(
                future,
                timeout=(
                    CONTROL_TIMEOUT_SECONDS
                ),
            )

            success = bool(
                result.get(
                    "success"
                )
            )

            with SessionLocal() as db:
                log_audit(
                    db,
                    user=user,
                    action=(
                        "PRINTER_STARTED"
                        if (
                            command == "start"
                            and success
                        )
                        else (
                            "PRINTER_STOPPED"
                            if success
                            else "PRINTER_COMMAND_FAILED"
                        )
                    ),
                    category="PRINTER_CONTROL",
                    outcome=(
                        "SUCCESS"
                        if success
                        else "FAILURE"
                    ),
                    object_type="device",
                    object_id=device_id,
                    details=result.get(
                        "message"
                    ),
                    request=request,
                    new_value=result.get(
                        "status"
                    ),
                    error_message=(
                        None
                        if success
                        else result.get(
                            "error"
                        )
                    ),
                )

                db.commit()

            if not success:
                raise HTTPException(
                    status_code=502,
                    detail=(
                        result.get(
                            "error"
                        )
                        or "Printer command failed"
                    ),
                )

            return {
                "success": True,
                "command": command,
                "device_id": device_id,
                "status": result.get(
                    "status"
                ),
                "message": result.get(
                    "message"
                ),
            }

        except asyncio.TimeoutError:
            write_audit_event(
                actor_email=user.email,
                actor_role=user.role,
                category="PRINTER_CONTROL",
                action="PRINTER_COMMAND_TIMEOUT",
                outcome="FAILURE",
                object_type="device",
                object_id=device_id,
                details=f"Command {command}",
            )

            raise HTTPException(
                status_code=504,
                detail=(
                    "Printer command timed out"
                ),
            )

        finally:
            _pending_commands.pop(
                command_id,
                None,
            )
