import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)

from pydantic import BaseModel
from sqlalchemy import desc, select

from .audit import (
    log_audit,
    write_audit_event,
)
from .audit_middleware import (
    AuditMiddleware,
)

from .alerts import evaluate_measurement, set_alert
from .database import Base, SessionLocal, engine
from .models import (
    Alert,
    Configuration,
    Customer,
    Device,
    DeviceConfiguration,
    Measurement,
    User,
)

from .auth import (
    create_access_token,
    get_current_user,
    require_technician,
    verify_password,
)


OFFLINE_CHECK_INTERVAL = 5


class LoginRequest(BaseModel):
    email: str
    password: str




def utc_now():
    return datetime.now(timezone.utc)


def make_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value


def get_configuration(db):
    config = db.get(Configuration, 1)

    if config is None:
        config = Configuration(
            id=1,
            collector_interval_seconds=5,
            offline_timeout_seconds=15,
            temperature_low=18.0,
            temperature_high=27.5,
            pressure_low=0.246,
            pressure_high=0.260,
            ink_low=70,
            makeup_low=60,
            printer_mode="simulator",
            printer_host="127.0.0.1",
            printer_port=1502,
            device_id=1,
        )

        db.add(config)
        db.commit()
        db.refresh(config)

    return config


async def offline_monitor():
    while True:
        await asyncio.sleep(
            OFFLINE_CHECK_INTERVAL
        )

        now = utc_now()

        with SessionLocal() as db:
            config = get_configuration(db)

            devices = db.scalars(
                select(Device)
            ).all()

            changed = False

            for device in devices:
                if device.last_seen is None:
                    continue

                device_config = db.get(
                    DeviceConfiguration,
                    device.device_id,
                )

                offline_after_seconds = (
                    device_config
                    .offline_timeout_seconds
                    if device_config
                    is not None
                    else config
                    .offline_timeout_seconds
                )

                last_seen = make_aware(
                    device.last_seen
                )

                seconds_since_seen = (
                    now - last_seen
                ).total_seconds()

                is_offline = (
                    seconds_since_seen
                    > offline_after_seconds
                )

                if is_offline:
                    if device.online:
                        print(
                            f"Device OFFLINE: "
                            f"{device.device_id}"
                        )

                    device.online = False

                    set_alert(
                        db,
                        device_id=device.device_id,
                        alert_type="offline",
                        severity="critical",
                        message=(
                            "No measurement received "
                            f"for more than "
                            f"{offline_after_seconds} "
                            "seconds"
                        ),
                        active=True,
                    )

                    changed = True

            if changed:
                db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(
        bind=engine
    )

    with SessionLocal() as db:
        get_configuration(db)

    write_audit_event(
        actor_email="SYSTEM",
        actor_role="SYSTEM",
        category="SYSTEM",
        action="SYSTEM_START",
        outcome="SUCCESS",
        object_type="backend",
        object_id="care-inspector-api",
    )

    monitor_task = asyncio.create_task(
        offline_monitor()
    )

    yield

    monitor_task.cancel()

    try:
        await monitor_task
    except asyncio.CancelledError:
        pass


    write_audit_event(
        actor_email="SYSTEM",
        actor_role="SYSTEM",
        category="SYSTEM",
        action="SYSTEM_STOP",
        outcome="SUCCESS",
        object_type="backend",
        object_id="care-inspector-api",
    )


app = FastAPI(
    title="Care-Inspector API",
    version="0.3.0",
    lifespan=lifespan,
)


app.add_middleware(
    AuditMiddleware
)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "care-inspector-backend",
        "version": "0.3.0",
    }


@app.get("/api/devices")
async def devices():
    with SessionLocal() as db:
        rows = db.scalars(
            select(Device)
            .order_by(Device.device_id)
        ).all()

        customers = db.scalars(
            select(Customer)
        ).all()

        customer_names = {
            customer.id: customer.name
            for customer in customers
        }

        return [
            {
                "device_id": d.device_id,

                "customer_id": (
                    d.customer_id
                ),

                "customer_name": (
                    customer_names.get(
                        d.customer_id
                    )
                    if d.customer_id
                    is not None
                    else None
                ),

                "display_name": (
                    d.display_name
                ),

                "location": (
                    d.location
                ),

                "source": d.source,
                "online": d.online,
                "status": d.status,

                "last_seen": (
                    d.last_seen.isoformat()
                    if d.last_seen
                    else None
                ),

                "print_count": (
                    d.print_count
                ),

                "temperature_c": (
                    d.temperature_c
                ),

                "pressure_mpa": (
                    d.pressure_mpa
                ),

                "ink_level_percent": (
                    d.ink_level_percent
                ),

                "makeup_level_percent": (
                    d.makeup_level_percent
                ),

                "model_name": (
                    d.model_name
                ),

                "serial_number": (
                    d.serial_number
                ),

                "ink_name": (
                    d.ink_name
                ),

                "ink_operating_time_hours": (
                    d.ink_operating_time_hours
                ),

                "cumulative_operation_time_hours": (
                    d.cumulative_operation_time_hours
                ),

                "ink_remaining_raw": (
                    d.ink_remaining_raw
                ),

                "ink_remaining_label": (
                    d.ink_remaining_label
                ),

                "makeup_remaining_raw": (
                    d.makeup_remaining_raw
                ),

                "makeup_remaining_label": (
                    d.makeup_remaining_label
                ),
            }
            for d in rows
        ]


@app.get("/api/measurements")
async def measurements(
    limit: int = 500,
    device_id: str | None = None,
    from_time: datetime | None = None,
    to_time: datetime | None = None,
):
    limit = max(
        1,
        min(limit, 5000),
    )

    with SessionLocal() as db:
        query = select(Measurement)

        if device_id:
            query = query.where(
                Measurement.device_id
                == device_id
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
            {
                "id": m.id,
                "device_id": m.device_id,
                "source": m.source,
                "online": m.online,
                "status": m.status,
                "print_count": (
                    m.print_count
                ),
                "temperature_c": (
                    m.temperature_c
                ),
                "pressure_mpa": (
                    m.pressure_mpa
                ),
                "ink_level_percent": (
                    m.ink_level_percent
                ),
                "makeup_level_percent": (
                    m.makeup_level_percent
                ),

                "model_name": (
                    m.model_name
                ),

                "serial_number": (
                    m.serial_number
                ),

                "ink_name": (
                    m.ink_name
                ),

                "ink_operating_time_hours": (
                    m.ink_operating_time_hours
                ),

                "cumulative_operation_time_hours": (
                    m.cumulative_operation_time_hours
                ),

                "ink_remaining_raw": (
                    m.ink_remaining_raw
                ),

                "ink_remaining_label": (
                    m.ink_remaining_label
                ),

                "makeup_remaining_raw": (
                    m.makeup_remaining_raw
                ),

                "makeup_remaining_label": (
                    m.makeup_remaining_label
                ),

                "timestamp": (
                    m.timestamp.isoformat()
                ),
            }
            for m in rows
        ]


# Kept because the Overview frontend
# currently uses this endpoint.
@app.get(
    "/api/measurements/latest"
)
async def latest_measurements(
    limit: int = 20,
):
    limit = max(
        1,
        min(limit, 500),
    )

    with SessionLocal() as db:
        rows = db.scalars(
            select(Measurement)
            .order_by(
                desc(
                    Measurement.timestamp
                )
            )
            .limit(limit)
        ).all()

        return [
            {
                "id": m.id,
                "device_id": m.device_id,
                "source": m.source,
                "online": m.online,
                "status": m.status,
                "print_count": (
                    m.print_count
                ),
                "temperature_c": (
                    m.temperature_c
                ),
                "pressure_mpa": (
                    m.pressure_mpa
                ),
                "ink_level_percent": (
                    m.ink_level_percent
                ),
                "makeup_level_percent": (
                    m.makeup_level_percent
                ),
                "timestamp": (
                    m.timestamp.isoformat()
                ),
            }
            for m in rows
        ]


@app.get("/api/alerts")
async def alerts(
    limit: int = 100,
    status: str | None = None,
    severity: str | None = None,
    device_id: str | None = None,
):
    limit = max(
        1,
        min(limit, 500),
    )

    with SessionLocal() as db:
        query = select(Alert)

        if status == "active":
            query = query.where(
                Alert.active.is_(True)
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

        if device_id:
            query = query.where(
                Alert.device_id
                == device_id
            )

        rows = db.scalars(
            query
            .order_by(
                desc(Alert.created_at)
            )
            .limit(limit)
        ).all()

        return [
            {
                "id": a.id,
                "device_id": (
                    a.device_id
                ),
                "alert_type": (
                    a.alert_type
                ),
                "severity": (
                    a.severity
                ),
                "message": (
                    a.message
                ),
                "active": a.active,
                "created_at": (
                    a.created_at
                    .isoformat()
                ),
                "resolved_at": (
                    a.resolved_at
                    .isoformat()
                    if a.resolved_at
                    else None
                ),
            }
            for a in rows
        ]


@app.get(
    "/api/alerts/active"
)
async def active_alerts():
    with SessionLocal() as db:
        rows = db.scalars(
            select(Alert)
            .where(
                Alert.active.is_(True)
            )
            .order_by(
                desc(Alert.created_at)
            )
        ).all()

        return [
            {
                "id": a.id,
                "device_id": (
                    a.device_id
                ),
                "alert_type": (
                    a.alert_type
                ),
                "severity": (
                    a.severity
                ),
                "message": (
                    a.message
                ),
                "created_at": (
                    a.created_at
                    .isoformat()
                ),
            }
            for a in rows
        ]


@app.get(
    "/api/configuration"
)
async def configuration():
    with SessionLocal() as db:
        config = get_configuration(db)

        return {
            "collector_interval_seconds": (
                config
                .collector_interval_seconds
            ),
            "offline_timeout_seconds": (
                config
                .offline_timeout_seconds
            ),
            "temperature_low": (
                config.temperature_low
            ),

            "temperature_high": (
                config.temperature_high
            ),
            "pressure_low": (
                config.pressure_low
            ),
            "pressure_high": (
                config.pressure_high
            ),
            "ink_low": (
                config.ink_low
            ),
            "makeup_low": (
                config.makeup_low
            ),
            "printer_mode": (
                config.printer_mode
            ),
            "printer_host": (
                config.printer_host
            ),
            "printer_port": (
                config.printer_port
            ),
            "device_id": (
                config.device_id
            ),
        }


@app.put(
    "/api/configuration"
)
async def update_configuration(
    data: dict,
):
    with SessionLocal() as db:
        config = get_configuration(db)

        config.collector_interval_seconds = int(
            data[
                "collector_interval_seconds"
            ]
        )

        config.offline_timeout_seconds = int(
            data[
                "offline_timeout_seconds"
            ]
        )

        config.temperature_low = float(
            data["temperature_low"]
        )

        config.temperature_high = float(
            data["temperature_high"]
        )

        config.pressure_low = float(
            data["pressure_low"]
        )

        config.pressure_high = float(
            data["pressure_high"]
        )

        config.ink_low = int(
            data["ink_low"]
        )

        config.makeup_low = int(
            data["makeup_low"]
        )

        config.printer_mode = str(
            data["printer_mode"]
        )

        config.printer_host = str(
            data["printer_host"]
        )

        config.printer_port = int(
            data["printer_port"]
        )

        config.device_id = int(
            data["device_id"]
        )

        db.commit()
        db.refresh(config)

        return {
            "status": "ok",
            "configuration": {
                "collector_interval_seconds": (
                    config
                    .collector_interval_seconds
                ),
                "offline_timeout_seconds": (
                    config
                    .offline_timeout_seconds
                ),
                "temperature_low": (
                    config.temperature_low
                ),
                "temperature_high": (
                    config.temperature_high
                ),
                "pressure_low": (
                    config.pressure_low
                ),
                "pressure_high": (
                    config.pressure_high
                ),
                "ink_low": (
                    config.ink_low
                ),
                "makeup_low": (
                    config.makeup_low
                ),
                "printer_mode": (
                    config.printer_mode
                ),
                "printer_host": (
                    config.printer_host
                ),
                "printer_port": (
                    config.printer_port
                ),
                "device_id": (
                    config.device_id
                ),
            },
        }


@app.websocket(
    "/ws/collector/{device_id}"
)
async def collector_websocket(
    websocket: WebSocket,
    device_id: str,
):
    await websocket.accept()

    write_audit_event(
        actor_email="SYSTEM",
        actor_role="SYSTEM",
        category="COLLECTOR",
        action="COLLECTOR_CONNECTED",
        outcome="SUCCESS",
        object_type="device",
        object_id=device_id,
        ip_address=(
            websocket.client.host
            if websocket.client
            else None
        ),
    )

    print(
        f"Collector connected: "
        f"{device_id}"
    )

    try:
        while True:
            data = (
                await websocket
                .receive_json()
            )

            timestamp = (
                datetime.fromisoformat(
                    data["timestamp"]
                )
            )

            with SessionLocal() as db:
                measurement = Measurement(
                    device_id=data[
                        "device_id"
                    ],
                    source=data[
                        "source"
                    ],
                    online=True,
                    status=data[
                        "status"
                    ],
                    print_count=data[
                        "print_count"
                    ],
                    temperature_c=data[
                        "temperature_c"
                    ],
                    pressure_mpa=data[
                        "pressure_mpa"
                    ],
                    ink_level_percent=data[
                        "ink_level_percent"
                    ],
                    makeup_level_percent=data[
                        "makeup_level_percent"
                    ],

                    model_name=data.get(
                        "model_name"
                    ),

                    serial_number=data.get(
                        "serial_number"
                    ),

                    ink_name=data.get(
                        "ink_name"
                    ),

                    ink_operating_time_hours=data.get(
                        "ink_operating_time_hours"
                    ),

                    cumulative_operation_time_hours=data.get(
                        "cumulative_operation_time_hours"
                    ),

                    ink_remaining_raw=data.get(
                        "ink_remaining_raw"
                    ),

                    ink_remaining_label=data.get(
                        "ink_remaining_label"
                    ),

                    makeup_remaining_raw=data.get(
                        "makeup_remaining_raw"
                    ),

                    makeup_remaining_label=data.get(
                        "makeup_remaining_label"
                    ),

                    timestamp=timestamp,
                )

                db.add(measurement)

                device = db.get(
                    Device,
                    device_id,
                )

                if device is None:
                    device = Device(
                        device_id=device_id,
                        source=data[
                            "source"
                        ],
                        online=True,
                        status=data[
                            "status"
                        ],
                        last_seen=timestamp,
                        print_count=data[
                            "print_count"
                        ],
                        temperature_c=data[
                            "temperature_c"
                        ],
                        pressure_mpa=data[
                            "pressure_mpa"
                        ],
                        ink_level_percent=data[
                            "ink_level_percent"
                        ],
                        makeup_level_percent=data[
                            "makeup_level_percent"
                        ],

                        model_name=data.get(
                            "model_name"
                        ),

                        serial_number=data.get(
                            "serial_number"
                        ),

                        ink_name=data.get(
                            "ink_name"
                        ),

                        ink_operating_time_hours=data.get(
                            "ink_operating_time_hours"
                        ),

                        cumulative_operation_time_hours=data.get(
                            "cumulative_operation_time_hours"
                        ),

                        ink_remaining_raw=data.get(
                            "ink_remaining_raw"
                        ),

                        ink_remaining_label=data.get(
                            "ink_remaining_label"
                        ),

                        makeup_remaining_raw=data.get(
                            "makeup_remaining_raw"
                        ),

                        makeup_remaining_label=data.get(
                            "makeup_remaining_label"
                        ),
                    )

                    db.add(device)

                else:
                    device.source = data[
                        "source"
                    ]

                    device.online = True

                    device.status = data[
                        "status"
                    ]

                    device.last_seen = (
                        timestamp
                    )

                    device.print_count = data[
                        "print_count"
                    ]

                    device.temperature_c = data[
                        "temperature_c"
                    ]

                    device.pressure_mpa = data[
                        "pressure_mpa"
                    ]

                    device.ink_level_percent = data[
                        "ink_level_percent"
                    ]

                    device.makeup_level_percent = data[
                        "makeup_level_percent"
                    ]

                    device.model_name = data.get(
                        "model_name"
                    )

                    device.serial_number = data.get(
                        "serial_number"
                    )

                    device.ink_name = data.get(
                        "ink_name"
                    )

                    device.ink_operating_time_hours = (
                        data.get(
                            "ink_operating_time_hours"
                        )
                    )

                    device.cumulative_operation_time_hours = (
                        data.get(
                            "cumulative_operation_time_hours"
                        )
                    )

                    device.ink_remaining_raw = data.get(
                        "ink_remaining_raw"
                    )

                    device.ink_remaining_label = data.get(
                        "ink_remaining_label"
                    )

                    device.makeup_remaining_raw = data.get(
                        "makeup_remaining_raw"
                    )

                    device.makeup_remaining_label = data.get(
                        "makeup_remaining_label"
                    )

                # Receiving data means the
                # printer is no longer offline.
                set_alert(
                    db,
                    device_id=device_id,
                    alert_type="offline",
                    severity="critical",
                    message="Device offline",
                    active=False,
                )

                config = (
                    get_configuration(db)
                )

                evaluate_measurement(
                    db,
                    data,
                    config,
                )

                db.commit()

            await websocket.send_json(
                {
                    "status": "stored",
                    "device_id": device_id,
                    "timestamp": data.get(
                        "timestamp"
                    ),
                }
            )

            print(
                f"Measurement stored: "
                f"{device_id} | "
                f"prints="
                f"{data['print_count']}"
            )

    except WebSocketDisconnect:
        write_audit_event(
            actor_email="SYSTEM",
            actor_role="SYSTEM",
            category="COLLECTOR",
            action="COLLECTOR_DISCONNECTED",
            outcome="SUCCESS",
            object_type="device",
            object_id=device_id,
        )

        print(
            f"Collector disconnected: "
            f"{device_id}"
        )

    except Exception as exc:
        write_audit_event(
            actor_email="SYSTEM",
            actor_role="SYSTEM",
            category="COLLECTOR",
            action="COLLECTOR_ERROR",
            outcome="FAILURE",
            object_type="device",
            object_id=device_id,
            error_message=str(exc),
        )

        print(
            f"Collector WebSocket error "
            f"for {device_id}: {exc}"
        )

        try:
            await websocket.close()
        except Exception:
            pass



# =========================================================
# Authentication
# =========================================================

@app.post("/api/auth/login")
async def login(
    request: LoginRequest,
    http_request: Request,
):
    email = (
        request.email
        .strip()
        .lower()
    )

    with SessionLocal() as db:
        user = db.scalar(
            select(User).where(
                User.email == email
            )
        )

        if (
            user is None
            or not user.active
            or not verify_password(
                request.password,
                user.password_hash,
            )
        ):
            log_audit(
                db,
                user=user,
                actor_email=email,
                actor_role=(
                    user.role
                    if user
                    else "ANONYMOUS"
                ),
                category="AUTH",
                action="LOGIN_FAILED",
                outcome="FAILURE",
                object_type="user",
                object_id=(
                    user.id
                    if user
                    else None
                ),
                request=http_request,
                status_code=401,
                details=(
                    "Invalid credentials "
                    "or inactive account"
                ),
            )

            db.commit()

            raise HTTPException(
                status_code=401,
                detail="Invalid email or password",
            )

        token = create_access_token(
            user
        )

        log_audit(
            db,
            user=user,
            category="AUTH",
            action="LOGIN_SUCCESS",
            outcome="SUCCESS",
            object_type="user",
            object_id=user.id,
            request=http_request,
            status_code=200,
        )

        db.commit()

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "role": user.role,
                "customer_id": (
                    user.customer_id
                ),
            },
        }


@app.get("/api/auth/me")
async def auth_me(
    user: User = Depends(
        get_current_user
    ),
):
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "customer_id": (
            user.customer_id
        ),
    }


@app.post("/api/auth/logout")
async def logout(
    http_request: Request,
    user: User = Depends(
        get_current_user
    ),
):
    with SessionLocal() as db:
        log_audit(
            db,
            user=user,
            category="AUTH",
            action="LOGOUT",
            outcome="SUCCESS",
            object_type="user",
            object_id=user.id,
            request=http_request,
            status_code=200,
        )

        db.commit()

    return {
        "status": "ok",
    }


# =========================================================
# Secure device access
# =========================================================

@app.get("/api/secure/devices")
async def secure_devices(
    user: User = Depends(
        get_current_user
    ),
):
    with SessionLocal() as db:

        query = select(Device)

        if user.role == "CUSTOMER":

            if user.customer_id is None:
                return []

            query = query.where(
                Device.customer_id
                == user.customer_id
            )

        elif user.role in {
            "TECHNICIAN",
            "ADMIN",
        }:
            pass

        else:
            raise HTTPException(
                status_code=403,
                detail="Unsupported user role",
            )

        rows = db.scalars(
            query.order_by(
                Device.device_id
            )
        ).all()

        customers = db.scalars(
            select(Customer)
        ).all()

        customer_names = {
            customer.id: customer.name
            for customer in customers
        }

        return [
            {
                "device_id": d.device_id,

                "display_name": (
                    d.display_name
                ),

                "customer_id": (
                    d.customer_id
                ),

                "customer_name": (
                    customer_names.get(
                        d.customer_id
                    )
                    if d.customer_id
                    is not None
                    else None
                ),

                "location": (
                    d.location
                ),

                "source": d.source,
                "online": d.online,
                "status": d.status,

                "last_seen": (
                    d.last_seen.isoformat()
                    if d.last_seen
                    else None
                ),

                "model_name": (
                    d.model_name
                ),

                "serial_number": (
                    d.serial_number
                ),

                "ink_name": (
                    d.ink_name
                ),

                "print_count": (
                    d.print_count
                ),

                "temperature_c": (
                    d.temperature_c
                ),

                "pressure_mpa": (
                    d.pressure_mpa
                ),

                "ink_operating_time_hours": (
                    d.ink_operating_time_hours
                ),

                "cumulative_operation_time_hours": (
                    d.cumulative_operation_time_hours
                ),

                "ink_remaining_raw": (
                    d.ink_remaining_raw
                ),

                "ink_remaining_label": (
                    d.ink_remaining_label
                ),

                "makeup_remaining_raw": (
                    d.makeup_remaining_raw
                ),

                "makeup_remaining_label": (
                    d.makeup_remaining_label
                ),
            }
            for d in rows
        ]


# =========================================================
# Technician customer access
# =========================================================

@app.get("/api/secure/customers")
async def secure_customers(
    user: User = Depends(
        get_current_user
    ),
):
    require_technician(
        user
    )

    with SessionLocal() as db:

        rows = db.scalars(
            select(Customer)
            .order_by(Customer.name)
        ).all()

        return [
            {
                "id": customer.id,
                "name": customer.name,

                "address": (
                    customer.address
                ),

                "contact_name": (
                    customer.contact_name
                ),

                "contact_email": (
                    customer.contact_email
                ),

                "contact_phone": (
                    customer.contact_phone
                ),

                "active": (
                    customer.active
                ),
            }
            for customer in rows
        ]


# Technician management API
from .management import router as management_router
app.include_router(management_router)


# Secure customer/technician data API
from .secure_data import router as secure_data_router
app.include_router(secure_data_router)

# Admin API
from .admin import router as admin_router
app.include_router(admin_router)


# Per-printer configuration API
from .device_configuration import (
    router as device_configuration_router,
)

app.include_router(
    device_configuration_router
)


# Printer control API / collector control channel
from .printer_control import (
    router as printer_control_router,
)

app.include_router(
    printer_control_router
)
