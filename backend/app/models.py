from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from .database import Base


class Measurement(Base):
    __tablename__ = "measurements"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    device_id: Mapped[str] = mapped_column(
        String,
        index=True,
    )

    source: Mapped[str] = mapped_column(
        String
    )

    online: Mapped[bool] = mapped_column(
        Boolean
    )

    status: Mapped[str] = mapped_column(
        String
    )

    print_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    temperature_c: Mapped[float] = mapped_column(
        Float
    )

    pressure_mpa: Mapped[float] = mapped_column(
        Float
    )

    ink_level_percent: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    makeup_level_percent: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    model_name: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    serial_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    ink_name: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    ink_operating_time_hours: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    cumulative_operation_time_hours: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    ink_remaining_raw: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    ink_remaining_label: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    makeup_remaining_raw: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    makeup_remaining_label: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
    )


class Device(Base):
    __tablename__ = "devices"

    device_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )

    source: Mapped[str] = mapped_column(
        String
    )

    online: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    status: Mapped[str] = mapped_column(
        String,
        default="unknown",
    )

    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True)
    )

    print_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    temperature_c: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    pressure_mpa: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    ink_level_percent: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    makeup_level_percent: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    model_name: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    serial_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    ink_name: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    ink_operating_time_hours: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    cumulative_operation_time_hours: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    ink_remaining_raw: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    ink_remaining_label: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    makeup_remaining_raw: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    makeup_remaining_label: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    customer_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )

    display_name: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    location: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    address: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    contact_name: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    contact_email: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    contact_phone: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    email: Mapped[str] = mapped_column(
        String,
        unique=True,
        index=True,
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="CUSTOMER",
    )

    customer_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )



class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    actor_user_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )

    actor_email: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )

    actor_role: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )

    category: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )

    action: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )

    outcome: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )

    object_type: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    object_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    method: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    path: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )

    status_code: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    ip_address: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    details: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    old_value: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    new_value: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    device_id: Mapped[str] = mapped_column(
        String,
        index=True,
    )

    alert_type: Mapped[str] = mapped_column(
        String,
        index=True,
    )

    severity: Mapped[str] = mapped_column(
        String
    )

    message: Mapped[str] = mapped_column(
        String
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True)
    )

    resolved_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


    acknowledged_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    acknowledged_by: Mapped[
        str | None
    ] = mapped_column(
        String,
        nullable=True,
    )


class Configuration(Base):
    __tablename__ = "configuration"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        default=1,
    )

    collector_interval_seconds: Mapped[int] = mapped_column(
        Integer,
        default=5,
    )

    offline_timeout_seconds: Mapped[int] = mapped_column(
        Integer,
        default=15,
    )

    temperature_low: Mapped[float] = mapped_column(
        Float,
        default=18.0,
    )

    temperature_high: Mapped[float] = mapped_column(
        Float,
        default=27.5,
    )

    pressure_low: Mapped[float] = mapped_column(
        Float,
        default=0.246,
    )

    pressure_high: Mapped[float] = mapped_column(
        Float,
        default=0.260,
    )

    ink_low: Mapped[int] = mapped_column(
        Integer,
        default=70,
    )

    makeup_low: Mapped[int] = mapped_column(
        Integer,
        default=60,
    )

    printer_mode: Mapped[str] = mapped_column(
        String,
        default="simulator",
    )

    printer_host: Mapped[str] = mapped_column(
        String,
        default="127.0.0.1",
    )

    printer_port: Mapped[int] = mapped_column(
        Integer,
        default=1502,
    )

    device_id: Mapped[int] = mapped_column(
        Integer,
        default=1,
    )


class DeviceConfiguration(Base):
    __tablename__ = "device_configurations"

    device_id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
    )

    collector_interval_seconds: Mapped[int] = mapped_column(
        Integer,
        default=5,
    )

    offline_timeout_seconds: Mapped[int] = mapped_column(
        Integer,
        default=15,
    )

    temperature_low: Mapped[float] = mapped_column(
        Float,
        default=18.0,
    )

    temperature_high: Mapped[float] = mapped_column(
        Float,
        default=27.5,
    )

    pressure_low: Mapped[float] = mapped_column(
        Float,
        default=0.246,
    )

    pressure_high: Mapped[float] = mapped_column(
        Float,
        default=0.260,
    )

    ink_low: Mapped[int] = mapped_column(
        Integer,
        default=70,
    )

    makeup_low: Mapped[int] = mapped_column(
        Integer,
        default=60,
    )
