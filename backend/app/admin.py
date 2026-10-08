from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from pydantic import BaseModel
from sqlalchemy import (
    func,
    select,
)

from .audit import log_audit
from .auth import (
    get_current_user,
    hash_password,
)
from .database import SessionLocal
from .models import (
    Alert,
    AuditLog,
    Customer,
    Device,
    User,
)


router = APIRouter(
    prefix="/api/secure/admin",
    tags=["admin"],
)


def require_admin(
    user: User,
):
    if user.role != "ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )


class UserCreate(BaseModel):
    email: str
    password: str
    role: str
    customer_id: int | None = None
    active: bool = True


class UserUpdate(BaseModel):
    email: str | None = None
    password: str | None = None
    role: str | None = None
    customer_id: int | None = None
    active: bool | None = None


def user_payload(
    user: User,
):
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "customer_id": user.customer_id,
        "active": user.active,
    }


def validate_role(
    role: str,
):
    allowed = {
        "ADMIN",
        "TECHNICIAN",
        "CUSTOMER",
    }

    if role not in allowed:
        raise HTTPException(
            status_code=400,
            detail="Invalid user role",
        )


def validate_customer(
    db,
    *,
    role: str,
    customer_id: int | None,
):
    if role == "CUSTOMER":
        if customer_id is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Customer users require "
                    "a customer assignment"
                ),
            )

        customer = db.get(
            Customer,
            customer_id,
        )

        if customer is None:
            raise HTTPException(
                status_code=404,
                detail="Customer not found",
            )

    elif customer_id is not None:
        raise HTTPException(
            status_code=400,
            detail=(
                "ADMIN and TECHNICIAN users "
                "must not have customer_id"
            ),
        )


@router.get("/dashboard")
async def admin_dashboard(
    user: User = Depends(
        get_current_user
    ),
):
    require_admin(user)

    with SessionLocal() as db:
        customers = db.scalar(
            select(
                func.count(Customer.id)
            )
        ) or 0

        users = db.scalar(
            select(
                func.count(User.id)
            )
        ) or 0

        devices = db.scalar(
            select(
                func.count(Device.device_id)
            )
        ) or 0

        online = db.scalar(
            select(
                func.count(Device.device_id)
            )
            .where(
                Device.online.is_(True)
            )
        ) or 0

        unassigned = db.scalar(
            select(
                func.count(Device.device_id)
            )
            .where(
                Device.customer_id.is_(None)
            )
        ) or 0

        active_alerts = db.scalar(
            select(
                func.count(Alert.id)
            )
            .where(
                Alert.active.is_(True)
            )
        ) or 0

        critical_alerts = db.scalar(
            select(
                func.count(Alert.id)
            )
            .where(
                Alert.active.is_(True),
                Alert.severity == "critical",
            )
        ) or 0

        return {
            "customers": customers,
            "users": users,
            "printers": devices,
            "online": online,
            "offline": max(
                devices - online,
                0,
            ),
            "unassigned": unassigned,
            "active_alerts": active_alerts,
            "critical_alerts": critical_alerts,
        }


@router.get("/users")
async def list_users(
    user: User = Depends(
        get_current_user
    ),
):
    require_admin(user)

    with SessionLocal() as db:
        rows = db.scalars(
            select(User)
            .order_by(User.email)
        ).all()

        return [
            user_payload(row)
            for row in rows
        ]


@router.post(
    "/users",
    status_code=201,
)
async def create_user(
    request: UserCreate,
    user: User = Depends(
        get_current_user
    ),
):
    require_admin(user)

    email = request.email.strip().lower()
    role = request.role.strip().upper()

    if not email:
        raise HTTPException(
            status_code=400,
            detail="Email is required",
        )

    if len(request.password) < 8:
        raise HTTPException(
            status_code=400,
            detail=(
                "Password must contain "
                "at least 8 characters"
            ),
        )

    validate_role(role)

    with SessionLocal() as db:
        existing = db.scalar(
            select(User)
            .where(
                User.email == email
            )
        )

        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail="Email already exists",
            )

        validate_customer(
            db,
            role=role,
            customer_id=(
                request.customer_id
            ),
        )

        row = User(
            email=email,
            password_hash=hash_password(
                request.password
            ),
            role=role,
            customer_id=(
                request.customer_id
                if role == "CUSTOMER"
                else None
            ),
            active=request.active,
        )

        db.add(row)
        db.flush()

        log_audit(
            db,
            user=user,
            action="USER_CREATED",
            object_type="user",
            object_id=row.id,
            details=(
                f"{email} / {role}"
            ),
        )

        db.commit()
        db.refresh(row)

        return user_payload(row)


@router.patch("/users/{user_id}")
async def update_user(
    user_id: int,
    request: UserUpdate,
    user: User = Depends(
        get_current_user
    ),
):
    require_admin(user)

    with SessionLocal() as db:
        row = db.get(
            User,
            user_id,
        )

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="User not found",
            )

        updates = request.model_dump(
            exclude_unset=True
        )

        next_role = (
            updates.get(
                "role",
                row.role,
            )
        )

        if next_role:
            next_role = (
                next_role
                .strip()
                .upper()
            )

        validate_role(next_role)

        next_customer_id = (
            updates.get(
                "customer_id",
                row.customer_id,
            )
        )

        if next_role != "CUSTOMER":
            next_customer_id = None

        validate_customer(
            db,
            role=next_role,
            customer_id=next_customer_id,
        )

        if (
            user_id == user.id
            and updates.get("active")
            is False
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "You cannot deactivate "
                    "your own admin account"
                ),
            )

        if (
            user_id == user.id
            and next_role != "ADMIN"
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "You cannot remove your "
                    "own admin role"
                ),
            )

        if "email" in updates:
            email = (
                updates["email"]
                .strip()
                .lower()
            )

            if not email:
                raise HTTPException(
                    status_code=400,
                    detail="Email is required",
                )

            duplicate = db.scalar(
                select(User)
                .where(
                    User.email == email,
                    User.id != user_id,
                )
            )

            if duplicate is not None:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Email already exists"
                    ),
                )

            row.email = email

        if "password" in updates:
            password = updates[
                "password"
            ]

            if (
                password is None
                or len(password) < 8
            ):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Password must contain "
                        "at least 8 characters"
                    ),
                )

            row.password_hash = (
                hash_password(
                    password
                )
            )

        row.role = next_role
        row.customer_id = next_customer_id

        if "active" in updates:
            row.active = updates[
                "active"
            ]

        log_audit(
            db,
            user=user,
            action="USER_UPDATED",
            object_type="user",
            object_id=row.id,
            details=(
                f"{row.email} / "
                f"{row.role} / "
                f"active={row.active}"
            ),
        )

        db.commit()
        db.refresh(row)

        return user_payload(row)


@router.get("/audit-log")
async def audit_log(
    limit: int = 500,
    category: str | None = None,
    outcome: str | None = None,
    action: str | None = None,
    actor_email: str | None = None,
    user: User = Depends(
        get_current_user
    ),
):
    require_admin(user)

    limit = max(
        1,
        min(limit, 2000),
    )

    with SessionLocal() as db:
        query = select(
            AuditLog
        )

        if category:
            query = query.where(
                AuditLog.category
                == category
            )

        if outcome:
            query = query.where(
                AuditLog.outcome
                == outcome
            )

        if action:
            query = query.where(
                AuditLog.action
                == action
            )

        if actor_email:
            query = query.where(
                AuditLog.actor_email
                == actor_email
            )

        rows = db.scalars(
            query
            .order_by(
                AuditLog.created_at.desc()
            )
            .limit(limit)
        ).all()

        return [
            {
                "id":
                    row.id,

                "actor_user_id":
                    row.actor_user_id,

                "actor_email":
                    row.actor_email,

                "actor_role":
                    row.actor_role,

                "category":
                    row.category,

                "action":
                    row.action,

                "outcome":
                    row.outcome,

                "object_type":
                    row.object_type,

                "object_id":
                    row.object_id,

                "method":
                    row.method,

                "path":
                    row.path,

                "status_code":
                    row.status_code,

                "ip_address":
                    row.ip_address,

                "details":
                    row.details,

                "old_value":
                    row.old_value,

                "new_value":
                    row.new_value,

                "error_message":
                    row.error_message,

                "created_at":
                    row.created_at.isoformat(),
            }
            for row in rows
        ]


@router.get("/system-health")
async def system_health(
    user: User = Depends(
        get_current_user
    ),
):
    require_admin(user)

    with SessionLocal() as db:
        db.scalar(
            select(func.count(User.id))
        )

        device_count = db.scalar(
            select(
                func.count(Device.device_id)
            )
        ) or 0

        online_count = db.scalar(
            select(
                func.count(Device.device_id)
            )
            .where(
                Device.online.is_(True)
            )
        ) or 0

        latest_device_seen = db.scalar(
            select(
                func.max(Device.last_seen)
            )
        )

        return {
            "api": "ok",
            "database": "ok",
            "timestamp":
                datetime.now(
                    timezone.utc
                ).isoformat(),
            "printers": device_count,
            "online_printers":
                online_count,
            "offline_printers":
                max(
                    device_count
                    - online_count,
                    0,
                ),
            "latest_device_seen": (
                latest_device_seen.isoformat()
                if latest_device_seen
                else None
            ),
        }
