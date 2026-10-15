from __future__ import annotations

import json

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
)

from pydantic import BaseModel

from .auth import (
    get_current_user,
    require_technician,
)

from .audit import log_audit
from .database import SessionLocal

from .models import (
    Configuration,
    Device,
    DeviceConfiguration,
    User,
)


router = APIRouter(
    prefix="/api/secure",
    tags=["device-configuration"],
)


class DeviceConfigurationUpdate(
    BaseModel
):
    collector_interval_seconds: int
    offline_timeout_seconds: int

    temperature_high: float
    pressure_low: float
    pressure_high: float

    ink_low: int
    makeup_low: int


FIELD_META = {
    "collector_interval_seconds": (
        "Collector interval",
        "sec",
    ),

    "offline_timeout_seconds": (
        "Offline timeout",
        "sec",
    ),

    "temperature_high": (
        "Temperature high",
        "°C",
    ),

    "pressure_low": (
        "Pressure low",
        "MPa",
    ),

    "pressure_high": (
        "Pressure high",
        "MPa",
    ),

    "ink_low": (
        "Ink low",
        "%",
    ),

    "makeup_low": (
        "Makeup low",
        "%",
    ),
}


def get_global_configuration(
    db,
):
    config = db.get(
        Configuration,
        1,
    )

    if config is None:
        raise HTTPException(
            status_code=500,
            detail=(
                "Global configuration "
                "is unavailable"
            ),
        )

    return config


def require_device(
    db,
    device_id: str,
):
    device = db.get(
        Device,
        device_id,
    )

    if device is None:
        raise HTTPException(
            status_code=404,
            detail="Printer not found",
        )

    return device


def configuration_payload(
    device: Device,
    config,
    *,
    inherited: bool,
):
    return {
        "device_id":
            device.device_id,

        "display_name":
            device.display_name,

        "serial_number":
            device.serial_number,

        "model_name":
            device.model_name,

        "location":
            device.location,

        "source":
            device.source,

        "inherited":
            inherited,

        "configuration_status":
            (
                "default"
                if inherited
                else "custom"
            ),

        "collector_interval_seconds":
            config.collector_interval_seconds,

        "offline_timeout_seconds":
            config.offline_timeout_seconds,

        "temperature_high":
            config.temperature_high,

        "pressure_low":
            config.pressure_low,

        "pressure_high":
            config.pressure_high,

        "ink_low":
            config.ink_low,

        "makeup_low":
            config.makeup_low,
    }


def snapshot_configuration(
    config,
):
    return {
        "collector_interval_seconds":
            config.collector_interval_seconds,

        "offline_timeout_seconds":
            config.offline_timeout_seconds,

        "temperature_high":
            config.temperature_high,

        "pressure_low":
            config.pressure_low,

        "pressure_high":
            config.pressure_high,

        "ink_low":
            config.ink_low,

        "makeup_low":
            config.makeup_low,
    }


def change_summary(
    old_data,
    new_data,
):
    if old_data is None:
        return (
            "Created individual printer "
            "configuration"
        )

    changes = []

    for field, new_value in (
        new_data.items()
    ):
        old_value = old_data.get(
            field
        )

        if old_value == new_value:
            continue

        label, unit = FIELD_META[
            field
        ]

        changes.append(
            f"{label}: "
            f"{old_value} → "
            f"{new_value} {unit}"
        )

    if not changes:
        return "No configuration values changed"

    return "; ".join(
        changes
    )


@router.get(
    "/devices/{device_id}/configuration"
)
async def get_device_configuration(
    device_id: str,
    user: User = Depends(
        get_current_user
    ),
):
    require_technician(user)

    with SessionLocal() as db:
        device = require_device(
            db,
            device_id,
        )

        config = db.get(
            DeviceConfiguration,
            device_id,
        )

        if config is not None:
            return configuration_payload(
                device,
                config,
                inherited=False,
            )

        global_config = (
            get_global_configuration(
                db
            )
        )

        return configuration_payload(
            device,
            global_config,
            inherited=True,
        )


@router.put(
    "/devices/{device_id}/configuration"
)
async def update_device_configuration(
    device_id: str,
    data: DeviceConfigurationUpdate,
    http_request: Request,
    user: User = Depends(
        get_current_user
    ),
):
    require_technician(user)

    if (
        data.collector_interval_seconds
        < 1
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Collector interval must "
                "be at least 1 second"
            ),
        )

    if (
        data.offline_timeout_seconds
        < 5
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Offline timeout must be "
                "at least 5 seconds"
            ),
        )

    if (
        data.pressure_low
        >= data.pressure_high
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Pressure low must be "
                "lower than pressure high"
            ),
        )

    if not (
        0 <= data.ink_low <= 100
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Ink threshold must be "
                "between 0 and 100"
            ),
        )

    if not (
        0 <= data.makeup_low <= 100
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Makeup threshold must be "
                "between 0 and 100"
            ),
        )

    with SessionLocal() as db:
        device = require_device(
            db,
            device_id,
        )

        config = db.get(
            DeviceConfiguration,
            device_id,
        )

        old_data = None

        if config is not None:
            old_data = (
                snapshot_configuration(
                    config
                )
            )

        if config is None:
            config = (
                DeviceConfiguration(
                    device_id=device_id,
                )
            )

            db.add(config)

        config.collector_interval_seconds = (
            data.collector_interval_seconds
        )

        config.offline_timeout_seconds = (
            data.offline_timeout_seconds
        )

        config.temperature_high = (
            data.temperature_high
        )

        config.pressure_low = (
            data.pressure_low
        )

        config.pressure_high = (
            data.pressure_high
        )

        config.ink_low = (
            data.ink_low
        )

        config.makeup_low = (
            data.makeup_low
        )

        new_data = data.model_dump()

        printer_name = (
            device.display_name
            or device.device_id
        )

        serial_text = (
            str(device.serial_number)
            if device.serial_number
            is not None
            else "unknown"
        )

        summary = change_summary(
            old_data,
            new_data,
        )

        log_audit(
            db,
            user=user,
            category="DEVICE",
            action=(
                "DEVICE_CONFIGURATION_UPDATED"
            ),
            outcome="SUCCESS",
            object_type="device",
            object_id=device_id,
            request=http_request,
            status_code=200,
            details=(
                f"{printer_name} "
                f"(Serial {serial_text}) — "
                f"{summary}"
            ),
            old_value=(
                json.dumps(
                    old_data,
                    sort_keys=True,
                )
                if old_data
                else None
            ),
            new_value=json.dumps(
                new_data,
                sort_keys=True,
            ),
        )

        db.commit()
        db.refresh(config)

        return configuration_payload(
            device,
            config,
            inherited=False,
        )
