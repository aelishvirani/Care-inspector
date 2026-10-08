from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from sqlalchemy import (
    desc,
    select,
)

from .auth import get_current_user
from .audit import log_audit
from .database import SessionLocal
from .models import (
    Alert,
    Device,
    Measurement,
    User,
)


router = APIRouter(
    prefix="/api/secure",
    tags=["secure-data"],
)


def check_role(user: User):
    if user.role not in {
        "CUSTOMER",
        "TECHNICIAN",
        "ADMIN",
    }:
        raise HTTPException(
            status_code=403,
            detail="Unsupported user role",
        )


def require_device_access(
    db,
    user: User,
    device_id: str,
) -> Device:
    check_role(user)

    device = db.get(
        Device,
        device_id,
    )

    if device is None:
        raise HTTPException(
            status_code=404,
            detail="Printer not found",
        )

    if user.role == "CUSTOMER":
        if (
            user.customer_id is None
            or device.customer_id
            != user.customer_id
        ):
            # Intentionally use 404 rather than 403.
            # This avoids revealing whether another
            # customer's printer exists.
            raise HTTPException(
                status_code=404,
                detail="Printer not found",
            )

    return device


def device_payload(
    device: Device,
):
    return {
        "device_id":
            device.device_id,

        "display_name":
            device.display_name,

        "customer_id":
            device.customer_id,

        "location":
            device.location,

        "source":
            device.source,

        "online":
            device.online,

        "status":
            device.status,

        "last_seen":
            (
                device.last_seen.isoformat()
                if device.last_seen
                else None
            ),

        "model_name":
            device.model_name,

        "serial_number":
            device.serial_number,

        "ink_name":
            device.ink_name,

        "print_count":
            device.print_count,

        "temperature_c":
            device.temperature_c,

        "pressure_mpa":
            device.pressure_mpa,

        "ink_level_percent":
            device.ink_level_percent,

        "makeup_level_percent":
            device.makeup_level_percent,

        "ink_operating_time_hours":
            device.ink_operating_time_hours,

        "cumulative_operation_time_hours":
            device.cumulative_operation_time_hours,

        "ink_remaining_raw":
            device.ink_remaining_raw,

        "ink_remaining_label":
            device.ink_remaining_label,

        "makeup_remaining_raw":
            device.makeup_remaining_raw,

        "makeup_remaining_label":
            device.makeup_remaining_label,
    }


def measurement_payload(
    measurement: Measurement,
):
    return {
        "id":
            measurement.id,

        "device_id":
            measurement.device_id,

        "source":
            measurement.source,

        "online":
            measurement.online,

        "status":
            measurement.status,

        "print_count":
            measurement.print_count,

        "temperature_c":
            measurement.temperature_c,

        "pressure_mpa":
            measurement.pressure_mpa,

        "ink_level_percent":
            measurement.ink_level_percent,

        "makeup_level_percent":
            measurement.makeup_level_percent,

        "model_name":
            measurement.model_name,

        "serial_number":
            measurement.serial_number,

        "ink_name":
            measurement.ink_name,

        "ink_operating_time_hours":
            measurement.ink_operating_time_hours,

        "cumulative_operation_time_hours":
            measurement.cumulative_operation_time_hours,

        "ink_remaining_raw":
            measurement.ink_remaining_raw,

        "ink_remaining_label":
            measurement.ink_remaining_label,

        "makeup_remaining_raw":
            measurement.makeup_remaining_raw,

        "makeup_remaining_label":
            measurement.makeup_remaining_label,

        "timestamp":
            (
                measurement.timestamp.isoformat()
                if measurement.timestamp
                else None
            ),
    }


def alert_payload(
    alert: Alert,
):
    return {
        "id":
            alert.id,

        "device_id":
            alert.device_id,

        "alert_type":
            alert.alert_type,

        "severity":
            alert.severity,

        "message":
            alert.message,

        "active":
            alert.active,

        "created_at":
            (
                alert.created_at.isoformat()
                if alert.created_at
                else None
            ),

        "resolved_at":
            (
                alert.resolved_at.isoformat()
                if alert.resolved_at
                else None
            ),


        "acknowledged_at":
            (
                alert.acknowledged_at.isoformat()
                if alert.acknowledged_at
                else None
            ),

        "acknowledged_by":
            alert.acknowledged_by,
    }


@router.get(
    "/devices/{device_id}"
)
async def secure_device_detail(
    device_id: str,
    user: User = Depends(
        get_current_user
    ),
):
    with SessionLocal() as db:
        device = require_device_access(
            db,
            user,
            device_id,
        )

        return device_payload(
            device
        )


@router.get(
    "/measurements"
)
async def secure_measurements(
    limit: int = 500,
    device_id: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
    user: User = Depends(
        get_current_user
    ),
):
    check_role(user)

    limit = max(
        1,
        min(limit, 5000),
    )

    with SessionLocal() as db:

        query = select(
            Measurement
        )

        if device_id:
            require_device_access(
                db,
                user,
                device_id,
            )

            query = query.where(
                Measurement.device_id
                == device_id
            )

        elif user.role == "CUSTOMER":

            if user.customer_id is None:
                return []

            allowed_device_ids = (
                select(
                    Device.device_id
                )
                .where(
                    Device.customer_id
                    == user.customer_id
                )
            )

            query = query.where(
                Measurement.device_id.in_(
                    allowed_device_ids
                )
            )

        if from_time:
            query = query.where(
                Measurement.timestamp
                >= from_time
            )

        if to_time:
            query = query.where(
                Measurement.timestamp
                <= to_time
            )

        rows = db.scalars(
            query
            .order_by(
                desc(
                    Measurement.timestamp
                )
            )
            .limit(limit)
        ).all()

        return [
            measurement_payload(row)
            for row in rows
        ]


@router.get(
    "/alerts"
)
async def secure_alerts(
    limit: int = 100,
    status: str | None = None,
    severity: str | None = None,
    device_id: str | None = None,
    user: User = Depends(
        get_current_user
    ),
):
    check_role(user)

    limit = max(
        1,
        min(limit, 500),
    )

    with SessionLocal() as db:

        query = select(
            Alert
        )

        if device_id:
            require_device_access(
                db,
                user,
                device_id,
            )

            query = query.where(
                Alert.device_id
                == device_id
            )

        elif user.role == "CUSTOMER":

            if user.customer_id is None:
                return []

            allowed_device_ids = (
                select(
                    Device.device_id
                )
                .where(
                    Device.customer_id
                    == user.customer_id
                )
            )

            query = query.where(
                Alert.device_id.in_(
                    allowed_device_ids
                )
            )

        if status == "active":
            query = query.where(
                Alert.active.is_(True),
                Alert.acknowledged_at.is_(None),
            )

        elif status == "acknowledged":
            query = query.where(
                Alert.active.is_(True),
                Alert.acknowledged_at.is_not(None),
            )

        elif status == "resolved":
            query = query.where(
                Alert.active.is_(False)
            )

        if severity:
            query = query.where(
                Alert.severity
                == severity
            )

        rows = db.scalars(
            query
            .order_by(
                desc(
                    Alert.created_at
                )
            )
            .limit(limit)
        ).all()

        return [
            alert_payload(row)
            for row in rows
        ]



@router.post(
    "/alerts/{alert_id}/acknowledge"
)
async def acknowledge_alert(
    alert_id: int,
    user: User = Depends(
        get_current_user
    ),
):
    if user.role not in {
        "TECHNICIAN",
        "ADMIN",
    }:
        raise HTTPException(
            status_code=403,
            detail=(
                "Technician or admin "
                "access required"
            ),
        )

    with SessionLocal() as db:

        alert = db.get(
            Alert,
            alert_id,
        )

        if alert is None:
            raise HTTPException(
                status_code=404,
                detail="Alert not found",
            )

        require_device_access(
            db,
            user,
            alert.device_id,
        )

        if not alert.active:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Resolved alerts cannot "
                    "be acknowledged"
                ),
            )

        # Idempotent:
        # acknowledging the same alert again
        # keeps the original user/time
        # and does not create duplicate
        # audit entries.
        if alert.acknowledged_at is None:
            alert.acknowledged_at = (
                datetime.now(
                    timezone.utc
                )
            )

            alert.acknowledged_by = (
                user.email
            )

            log_audit(
                db,
                user=user,
                action="ALERT_ACKNOWLEDGED",
                object_type="alert",
                object_id=alert.id,
                details=(
                    f"{alert.alert_type} "
                    f"for {alert.device_id}"
                ),
            )

            db.commit()
            db.refresh(alert)

        return alert_payload(
            alert
        )
