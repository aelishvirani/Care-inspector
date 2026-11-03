"""Persistent untrusted Pi enrollment requests, not activated collectors.

A key-possession proof is not independent ownership verification. Pending
records cannot authenticate to the cloud or execute commands.
"""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base


class PiEnrollmentRequest(Base):
    __tablename__ = "pi_enrollment_requests"
    __table_args__ = (
        UniqueConstraint("hardware_id", name="uq_pi_enrollment_hardware"),
        UniqueConstraint("public_key_b64", name="uq_pi_enrollment_key"),
    )

    enrollment_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    pairing_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pi_pairing_attempts.pairing_id"),
        nullable=False, unique=True
    )
    hardware_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    public_key_b64: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_by_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="pending_ownership_review"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reviewed_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
