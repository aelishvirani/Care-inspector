from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .auth import get_current_user, require_technician
from .audit import log_audit
from .database import SessionLocal
from .device_groups import DeviceGroup, DeviceGroupMembership, UserGroupAccess
from .models import Customer, Device, User


router = APIRouter(
    prefix="/api/secure/management/device-groups",
    tags=["device-groups"],
)


class GroupCreate(BaseModel):
    customer_id: int
    name: str
    description: str | None = None


def group_payload(group: DeviceGroup):
    return {
        "id": group.id,
        "customer_id": group.customer_id,
        "name": group.name,
        "description": group.description,
        "created_at": group.created_at.isoformat(),
    }


@router.get("")
def list_groups(
    customer_id: int | None = None,
    user: User = Depends(get_current_user),
):
    require_technician(user)

    with SessionLocal() as db:
        query = select(DeviceGroup)

        if customer_id is not None:
            query = query.where(
                DeviceGroup.customer_id == customer_id
            )

        groups = db.scalars(
            query.order_by(
                DeviceGroup.customer_id,
                DeviceGroup.name,
            )
        ).all()

        return [group_payload(group) for group in groups]


@router.post("", status_code=201)
def create_group(
    request: GroupCreate,
    user: User = Depends(get_current_user),
):
    require_technician(user)

    name = request.name.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Group name is required",
        )

    with SessionLocal() as db:
        customer = db.get(Customer, request.customer_id)

        if customer is None:
            raise HTTPException(
                status_code=404,
                detail="Customer not found",
            )

        group = DeviceGroup(
            customer_id=request.customer_id,
            name=name,
            description=request.description,
        )

        db.add(group)

        try:
            db.flush()

            log_audit(
                db,
                user=user,
                category="MANAGEMENT",
                action="DEVICE_GROUP_CREATED",
                object_type="device_group",
                object_id=group.id,
                details=(
                    f"name={name}; "
                    f"customer_id={request.customer_id}"
                ),
            )

            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="Group name already exists for this customer",
            )

        db.refresh(group)
        return group_payload(group)



@router.get("/{group_id}/devices")
def list_group_devices(
    group_id: int,
    user: User = Depends(get_current_user),
):
    require_technician(user)

    with SessionLocal() as db:
        group = db.get(DeviceGroup, group_id)

        if group is None:
            raise HTTPException(404, "Group not found")

        rows = db.execute(
            select(Device)
            .join(
                DeviceGroupMembership,
                Device.device_id == DeviceGroupMembership.device_id,
            )
            .where(DeviceGroupMembership.group_id == group_id)
            .where(Device.customer_id == group.customer_id)
            .order_by(Device.device_id)
        ).scalars().all()

        return [
            {
                "device_id": device.device_id,
                "display_name": device.display_name,
                "customer_id": device.customer_id,
                "status": device.status,
                "online": device.online,
            }
            for device in rows
        ]


@router.post("/{group_id}/devices/{device_id}", status_code=201)
def assign_group_device(
    group_id: int,
    device_id: str,
    user: User = Depends(get_current_user),
):
    require_technician(user)

    with SessionLocal() as db:
        group = db.get(DeviceGroup, group_id)
        if group is None:
            raise HTTPException(404, "Group not found")

        device = db.get(Device, device_id)
        if device is None:
            raise HTTPException(404, "Printer not found")

        if device.customer_id != group.customer_id:
            raise HTTPException(
                403,
                "Printer belongs to another customer or is unassigned",
            )

        existing = db.get(
            DeviceGroupMembership,
            (group_id, device_id),
        )

        if existing is not None:
            raise HTTPException(409, "Printer already belongs to group")

        membership = DeviceGroupMembership(
            group_id=group_id,
            device_id=device_id,
        )
        db.add(membership)

        log_audit(
            db,
            user=user,
            category="MANAGEMENT",
            action="DEVICE_GROUP_PRINTER_ASSIGNED",
            object_type="device_group",
            object_id=group_id,
            details=f"device_id={device_id}",
        )

        db.commit()

        return {
            "group_id": group_id,
            "device_id": device_id,
            "assigned": True,
        }


@router.delete("/{group_id}/devices/{device_id}")
def remove_group_device(
    group_id: int,
    device_id: str,
    user: User = Depends(get_current_user),
):
    require_technician(user)

    with SessionLocal() as db:
        group = db.get(DeviceGroup, group_id)
        if group is None:
            raise HTTPException(404, "Group not found")

        membership = db.get(
            DeviceGroupMembership,
            (group_id, device_id),
        )

        if membership is None:
            raise HTTPException(404, "Group membership not found")

        db.delete(membership)

        log_audit(
            db,
            user=user,
            category="MANAGEMENT",
            action="DEVICE_GROUP_PRINTER_REMOVED",
            object_type="device_group",
            object_id=group_id,
            details=f"device_id={device_id}",
        )

        db.commit()

        return {
            "group_id": group_id,
            "device_id": device_id,
            "removed": True,
        }



@router.get("/{group_id}/users")
def list_group_users(
    group_id: int,
    user: User = Depends(get_current_user),
):
    require_technician(user)

    with SessionLocal() as db:
        group = db.get(DeviceGroup, group_id)
        if group is None:
            raise HTTPException(404, "Group not found")

        users = db.scalars(
            select(User)
            .join(
                UserGroupAccess,
                User.id == UserGroupAccess.user_id,
            )
            .where(UserGroupAccess.group_id == group_id)
            .where(User.customer_id == group.customer_id)
            .where(User.role == "CUSTOMER")
            .order_by(User.id)
        ).all()

        return [
            {
                "id": item.id,
                "email": item.email,
                "customer_id": item.customer_id,
            }
            for item in users
        ]


@router.post("/{group_id}/users/{user_id}", status_code=201)
def assign_group_user(
    group_id: int,
    user_id: int,
    user: User = Depends(get_current_user),
):
    require_technician(user)

    with SessionLocal() as db:
        group = db.get(DeviceGroup, group_id)
        target = db.get(User, user_id)

        if group is None:
            raise HTTPException(404, "Group not found")

        if target is None:
            raise HTTPException(404, "User not found")

        if (
            target.role != "CUSTOMER"
            or not target.active
            or target.customer_id != group.customer_id
        ):
            raise HTTPException(
                403,
                "User is not an active customer account belonging to this group",
            )

        if db.get(UserGroupAccess, (user_id, group_id)):
            raise HTTPException(409, "User already assigned")

        db.add(UserGroupAccess(
            user_id=user_id,
            group_id=group_id,
        ))

        log_audit(
            db,
            user=user,
            category="MANAGEMENT",
            action="DEVICE_GROUP_USER_ASSIGNED",
            object_type="device_group",
            object_id=group_id,
            details=f"user_id={user_id}",
        )

        db.commit()

        return {
            "group_id": group_id,
            "user_id": user_id,
            "assigned": True,
        }


@router.delete("/{group_id}/users/{user_id}")
def remove_group_user(
    group_id: int,
    user_id: int,
    user: User = Depends(get_current_user),
):
    require_technician(user)

    with SessionLocal() as db:
        group = db.get(DeviceGroup, group_id)

        if group is None:
            raise HTTPException(404, "Group not found")

        assignment = db.get(
            UserGroupAccess,
            (user_id, group_id),
        )

        if assignment is None:
            raise HTTPException(404, "Assignment not found")

        db.delete(assignment)

        log_audit(
            db,
            user=user,
            category="MANAGEMENT",
            action="DEVICE_GROUP_USER_REMOVED",
            object_type="device_group",
            object_id=group_id,
            details=f"user_id={user_id}",
        )

        db.commit()

        return {
            "group_id": group_id,
            "user_id": user_id,
            "removed": True,
        }
