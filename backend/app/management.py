from __future__ import annotations

from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from pydantic import BaseModel

from sqlalchemy import select

from .auth import (
    get_current_user,
    require_technician,
)

from .audit import log_audit
from .database import SessionLocal

from .models import (
    Customer,
    Device,
    User,
)


router = APIRouter(
    prefix="/api/secure/management",
    tags=["management"],
)


# =========================================================
# Request models
# =========================================================


class CustomerCreate(BaseModel):
    name: str
    address: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    active: bool = True


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    active: Optional[bool] = None


class DeviceCreate(BaseModel):
    device_id: str
    display_name: Optional[str] = None
    customer_id: Optional[int] = None
    location: Optional[str] = None
    model_name: Optional[str] = None
    serial_number: Optional[int] = None
    ink_name: Optional[str] = None


class DeviceUpdate(BaseModel):
    display_name: Optional[str] = None
    customer_id: Optional[int] = None
    location: Optional[str] = None
    model_name: Optional[str] = None
    serial_number: Optional[int] = None
    ink_name: Optional[str] = None


# =========================================================
# Serializers
# =========================================================


def customer_payload(
    customer: Customer,
):
    return {
        "id": customer.id,
        "name": customer.name,
        "address": customer.address,
        "contact_name": customer.contact_name,
        "contact_email": customer.contact_email,
        "contact_phone": customer.contact_phone,
        "active": customer.active,
    }


def device_payload(
    device: Device,
):
    return {
        "device_id": device.device_id,
        "display_name": device.display_name,
        "customer_id": device.customer_id,
        "location": device.location,

        "source": device.source,
        "online": device.online,
        "status": device.status,

        "last_seen": (
            device.last_seen.isoformat()
            if device.last_seen
            else None
        ),

        "model_name": device.model_name,
        "serial_number": device.serial_number,
        "ink_name": device.ink_name,

        "print_count": device.print_count,
        "temperature_c": device.temperature_c,
        "pressure_mpa": device.pressure_mpa,

        "ink_operating_time_hours": (
            device.ink_operating_time_hours
        ),

        "cumulative_operation_time_hours": (
            device.cumulative_operation_time_hours
        ),

        "ink_remaining_raw": (
            device.ink_remaining_raw
        ),

        "ink_remaining_label": (
            device.ink_remaining_label
        ),

        "makeup_remaining_raw": (
            device.makeup_remaining_raw
        ),

        "makeup_remaining_label": (
            device.makeup_remaining_label
        ),
    }


def require_customer(
    db,
    customer_id: int,
):
    customer = db.get(
        Customer,
        customer_id,
    )

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    return customer


# =========================================================
# Customers
# =========================================================


@router.get("/customers")
async def list_customers(
    user: User = Depends(
        get_current_user
    ),
):
    require_technician(user)

    with SessionLocal() as db:
        rows = db.scalars(
            select(Customer)
            .order_by(Customer.name)
        ).all()

        return [
            customer_payload(row)
            for row in rows
        ]


@router.post(
    "/customers",
    status_code=201,
)
async def create_customer(
    request: CustomerCreate,
    user: User = Depends(
        get_current_user
    ),
):
    require_technician(user)

    name = request.name.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Customer name is required",
        )

    with SessionLocal() as db:

        customer = Customer(
            name=name,
            address=request.address,
            contact_name=request.contact_name,
            contact_email=request.contact_email,
            contact_phone=request.contact_phone,
            active=request.active,
        )

        db.add(customer)
        db.flush()

        log_audit(
            db,
            user=user,
            action="CUSTOMER_CREATED",
            object_type="customer",
            object_id=customer.id,
            details=customer.name,
        )

        db.commit()
        db.refresh(customer)

        return customer_payload(
            customer
        )


@router.get(
    "/customers/{customer_id}"
)
async def get_customer(
    customer_id: int,
    user: User = Depends(
        get_current_user
    ),
):
    require_technician(user)

    with SessionLocal() as db:
        customer = require_customer(
            db,
            customer_id,
        )

        printers = db.scalars(
            select(Device)
            .where(
                Device.customer_id
                == customer_id
            )
            .order_by(
                Device.device_id
            )
        ).all()

        return {
            **customer_payload(
                customer
            ),

            "printers": [
                device_payload(row)
                for row in printers
            ],
        }


@router.patch(
    "/customers/{customer_id}"
)
async def update_customer(
    customer_id: int,
    request: CustomerUpdate,
    user: User = Depends(
        get_current_user
    ),
):
    require_technician(user)

    with SessionLocal() as db:

        customer = require_customer(
            db,
            customer_id,
        )

        updates = (
            request.model_dump(
                exclude_unset=True
            )
        )

        if (
            "name" in updates
            and updates["name"] is not None
        ):
            name = (
                updates["name"]
                .strip()
            )

            if not name:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Customer name "
                        "cannot be empty"
                    ),
                )

            updates["name"] = name

        for field, value in (
            updates.items()
        ):
            setattr(
                customer,
                field,
                value,
            )

        log_audit(
            db,
            user=user,
            action="CUSTOMER_UPDATED",
            object_type="customer",
            object_id=customer.id,
            details=(
                "Updated fields: "
                + ", ".join(
                    sorted(
                        updates.keys()
                    )
                )
            ),
        )

        db.commit()
        db.refresh(customer)

        return customer_payload(
            customer
        )


# =========================================================
# Printer registration / assignment
# =========================================================


@router.get("/devices")
async def list_devices(
    user: User = Depends(
        get_current_user
    ),
):
    require_technician(user)

    with SessionLocal() as db:

        rows = db.scalars(
            select(Device)
            .order_by(
                Device.device_id
            )
        ).all()

        return [
            device_payload(row)
            for row in rows
        ]


@router.post(
    "/devices",
    status_code=201,
)
async def register_device(
    request: DeviceCreate,
    user: User = Depends(
        get_current_user
    ),
):
    require_technician(user)

    device_id = (
        request.device_id
        .strip()
    )

    if not device_id:
        raise HTTPException(
            status_code=400,
            detail="Device ID is required",
        )

    with SessionLocal() as db:

        existing = db.get(
            Device,
            device_id,
        )

        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Device ID already exists"
                ),
            )

        if (
            request.customer_id
            is not None
        ):
            require_customer(
                db,
                request.customer_id,
            )

        device = Device(
            device_id=device_id,

            display_name=(
                request.display_name
            ),

            customer_id=(
                request.customer_id
            ),

            location=(
                request.location
            ),

            model_name=(
                request.model_name
            ),

            serial_number=(
                request.serial_number
            ),

            ink_name=(
                request.ink_name
            ),

            # The real collector will
            # overwrite these fields when
            # the device first connects.
            source="registered",
            online=False,
            status="registered",
        )

        db.add(device)

        log_audit(
            db,
            user=user,
            action="DEVICE_REGISTERED",
            object_type="device",
            object_id=device.device_id,
            details=(
                f"customer_id="
                f"{device.customer_id}"
            ),
        )

        db.commit()
        db.refresh(device)

        return device_payload(
            device
        )


@router.patch(
    "/devices/{device_id}"
)
async def update_device(
    device_id: str,
    request: DeviceUpdate,
    user: User = Depends(
        get_current_user
    ),
):
    require_technician(user)

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

        updates = (
            request.model_dump(
                exclude_unset=True
            )
        )

        old_customer_id = (
            device.customer_id
        )

        if (
            "customer_id"
            in updates
            and updates[
                "customer_id"
            ] is not None
        ):
            require_customer(
                db,
                updates[
                    "customer_id"
                ],
            )

        for field, value in (
            updates.items()
        ):
            setattr(
                device,
                field,
                value,
            )

        new_customer_id = (
            device.customer_id
        )

        if (
            old_customer_id is None
            and new_customer_id
            is not None
        ):
            action = "DEVICE_ASSIGNED"

        elif (
            old_customer_id
            is not None
            and new_customer_id
            is None
        ):
            action = "DEVICE_UNASSIGNED"

        else:
            action = "DEVICE_UPDATED"

        log_audit(
            db,
            user=user,
            category="DEVICE",
            action=action,
            outcome="SUCCESS",
            object_type="device",
            object_id=device.device_id,
            details=(
                "Printer management change"
            ),
            old_value=(
                f"customer_id="
                f"{old_customer_id}"
            ),
            new_value=(
                f"customer_id="
                f"{new_customer_id}"
            ),
        )

        db.commit()
        db.refresh(device)

        return device_payload(
            device
        )
