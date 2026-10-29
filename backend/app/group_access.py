from sqlalchemy import select

from .device_groups import (
    DeviceGroup,
    DeviceGroupMembership,
    UserGroupAccess,
)
from .models import Device, User


def allowed_device_ids(db, user: User):
    """Return authorized device IDs for a customer.

    None means unrestricted access for Technician/Admin.
    """
    if user.role in {"TECHNICIAN", "ADMIN"}:
        return None

    if user.role != "CUSTOMER":
        return set()

    if user.customer_id is None:
        return set()

    assigned_groups = set(db.scalars(
        select(UserGroupAccess.group_id)
        .join(
            DeviceGroup,
            UserGroupAccess.group_id == DeviceGroup.id,
        )
        .where(
            UserGroupAccess.user_id == user.id,
            DeviceGroup.customer_id == user.customer_id,
        )
    ).all())

    # No group assignment means no printer access.
    if not assigned_groups:
        return set()

    grouped_devices = set(db.scalars(
        select(DeviceGroupMembership.device_id)
        .join(
            DeviceGroup,
            DeviceGroupMembership.group_id == DeviceGroup.id,
        )
        .join(
            Device,
            Device.device_id == DeviceGroupMembership.device_id,
        )
        .where(
            DeviceGroupMembership.group_id.in_(assigned_groups),
            DeviceGroup.customer_id == user.customer_id,
            Device.customer_id == user.customer_id,
        )
    ).all())

    return grouped_devices
