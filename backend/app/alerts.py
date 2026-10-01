from datetime import datetime, timezone

from sqlalchemy import select

from .models import Alert


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
            db.add(
                Alert(
                    device_id=device_id,
                    alert_type=alert_type,
                    severity=severity,
                    message=message,
                    active=True,
                    created_at=utc_now(),
                    resolved_at=None,
                )
            )
        else:
            existing.message = message
            existing.severity = severity

    else:
        if existing is not None:
            existing.active = False
            existing.resolved_at = utc_now()


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
            alert_type="temperature_high",
            severity="warning",
            message=(
                f"Temperature high: "
                f"{temperature:.1f} °C"
            ),
            active=(
                temperature
                > config.temperature_high
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
                < config.pressure_low
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
                > config.pressure_high
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
                ink < config.ink_low
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
                makeup < config.makeup_low
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
