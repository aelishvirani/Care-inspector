from datetime import datetime, timezone

from sqlalchemy import select

from .audit import log_audit
from .notifications import notify_new_alert
from .models import (
    Alert,
    DeviceConfiguration,
)


def utc_now():
    return datetime.now(timezone.utc)


def set_alert(
    db,
    *,
    device_id: str,
    alert_type: str,
    severity: str,
    message: str,
    active: bool,
):
    existing = db.scalar(
        select(Alert).where(
            Alert.device_id == device_id,
            Alert.alert_type == alert_type,
            Alert.active.is_(True),
        )
    )

    if active:
        if existing is None:
            alert = Alert(
                device_id=device_id,
                alert_type=alert_type,
                severity=severity,
                message=message,
                active=True,
                created_at=utc_now(),
                resolved_at=None,
            )

            db.add(alert)
            db.flush()

            notify_new_alert(
                db,
                device_id=device_id,
                alert_type=alert_type,
                severity=severity,
                message=message,
            )

            log_audit(
                db,
                actor_email="SYSTEM",
                actor_role="SYSTEM",
                category="ALERT",
                action="ALERT_CREATED",
                outcome="SUCCESS",
                object_type="alert",
                object_id=alert.id,
                details=(
                    f"{alert_type} for "
                    f"{device_id}: "
                    f"{message}"
                ),
            )
        else:
            existing.message = message
            existing.severity = severity

    else:
        if existing is not None:
            existing.active = False
            existing.resolved_at = utc_now()

            log_audit(
                db,
                actor_email="SYSTEM",
                actor_role="SYSTEM",
                category="ALERT",
                action="ALERT_RESOLVED",
                outcome="SUCCESS",
                object_type="alert",
                object_id=existing.id,
                details=(
                    f"{alert_type} for "
                    f"{device_id}"
                ),
            )


def _optional_float(value):
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value):
    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def evaluate_measurement(
    db,
    data: dict,
    config,
):
    device_id = str(data["device_id"])

    device_config = db.get(
        DeviceConfiguration,
        device_id,
    )

    effective_config = (
        device_config
        if device_config is not None
        else config
    )

    temperature = _optional_float(
        data.get("temperature_c")
    )

    pressure = _optional_float(
        data.get("pressure_mpa")
    )

    ink = _optional_int(
        data.get("ink_level_percent")
    )

    makeup = _optional_int(
        data.get("makeup_level_percent")
    )

    status = str(
        data.get("status") or "unknown"
    ).lower()

    # Temperature
    if temperature is not None:
        set_alert(
            db,
            device_id=device_id,
            alert_type="temperature_low",
            severity="warning",
            message=(
                f"Temperature too low: "
                f"{temperature:.1f} °C"
            ),
            active=(
                temperature
                < effective_config.temperature_low
            ),
        )

        set_alert(
            db,
            device_id=device_id,
            alert_type="temperature_high",
            severity="warning",
            message=(
                f"Temperature too high: "
                f"{temperature:.1f} °C"
            ),
            active=(
                temperature
                > effective_config.temperature_high
            ),
        )

        # Pressure
    if (
        pressure is not None
        and status != "stopped"
    ):
        set_alert(
            db,
            device_id=device_id,
            alert_type="pressure_low",
            severity="warning",
            message=(
                f"Pressure too low: "
                f"{pressure:.3f} MPa"
            ),
            active=(
                pressure
                < effective_config.pressure_low
            ),
        )

        set_alert(
            db,
            device_id=device_id,
            alert_type="pressure_high",
            severity="warning",
            message=(
                f"Pressure too high: "
                f"{pressure:.3f} MPa"
            ),
            active=(
                pressure
                > effective_config.pressure_high
            ),
        )

    else:
        set_alert(
            db,
            device_id=device_id,
            alert_type="pressure_low",
            severity="warning",
            message=(
                "Pressure monitoring inactive "
                "while printer is stopped"
            ),
            active=False,
        )

        set_alert(
            db,
            device_id=device_id,
            alert_type="pressure_high",
            severity="warning",
            message=(
                "Pressure monitoring inactive "
                "while printer is stopped"
            ),
            active=False,
        )

    # Simulator currently provides percentage values.
    # Real Hitachi UX printers currently provide native
    # discrete ink/makeup levels instead, so None is valid.
    if ink is not None:
        set_alert(
            db,
            device_id=device_id,
            alert_type="ink_low",
            severity="warning",
            message=f"Ink level low: {ink}%",
            active=(
                ink < effective_config.ink_low
            ),
        )

    if makeup is not None:
        set_alert(
            db,
            device_id=device_id,
            alert_type="makeup_low",
            severity="warning",
            message=(
                f"Makeup level low: "
                f"{makeup}%"
            ),
            active=(
                makeup < effective_config.makeup_low
            ),
        )

    set_alert(
        db,
        device_id=device_id,
        alert_type="printer_warning",
        severity="warning",
        message="Printer reports WARNING status",
        active=(
            status == "warning"
        ),
    )

    set_alert(
        db,
        device_id=device_id,
        alert_type="printer_fault",
        severity="critical",
        message="Printer reports FAULT status",
        active=(
            status == "fault"
        ),
    )
