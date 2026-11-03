"""Staged, versioned Pi printer targets; no automatic application on the Pi."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base


class PiTargetConfiguration(Base):
    __tablename__ = "pi_target_configurations"
    hardware_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("pi_registered_devices.hardware_id"),
        primary_key=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    targets_json: Mapped[str] = mapped_column(Text, nullable=False)
    updated_by_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
