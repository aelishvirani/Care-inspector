from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class DeviceGroup(Base):
    __tablename__ = "device_groups"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True
    )
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String, nullable=False
    )
    description: Mapped[str | None] = mapped_column(
        String, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "customer_id", "name",
            name="uq_device_group_customer_name",
        ),
    )


class DeviceGroupMembership(Base):
    __tablename__ = "device_group_memberships"

    group_id: Mapped[int] = mapped_column(
        ForeignKey("device_groups.id"),
        primary_key=True,
    )
    device_id: Mapped[str] = mapped_column(
        ForeignKey("devices.device_id"),
        primary_key=True,
    )


class UserGroupAccess(Base):
    __tablename__ = "user_group_access"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        primary_key=True,
    )
    group_id: Mapped[int] = mapped_column(
        ForeignKey("device_groups.id"),
        primary_key=True,
    )
