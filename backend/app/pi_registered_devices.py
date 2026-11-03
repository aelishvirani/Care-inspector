"""Trusted-by-technician Pi key registrations; not yet cloud-authenticated agents.

Explicit technician authorization follows BLE key possession proof.
This is trust-on-first-use, not factory attestation. A subsequent
device-authenticated provisioning protocol is needed for cloud access.
"""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base


class PiRegisteredDevice(Base):
    __tablename__ = "pi_registered_devices"

    hardware_id: Mapped[str] = mapped_column(
        String(128), primary_key=True
    )
    public_key_b64: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )
    pairing_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pi_pairing_attempts.pairing_id"),
        nullable=False, unique=True
    )
    authorized_by_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="registered_awaiting_cloud_auth"
    )
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
