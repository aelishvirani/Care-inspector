"""Last cryptographically verified check-in for a registered Raspberry Pi."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base


class PiHeartbeat(Base):
    __tablename__ = "pi_heartbeats"
    hardware_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("pi_registered_devices.hardware_id"),
        primary_key=True,
    )
    last_authenticated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
