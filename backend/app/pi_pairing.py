"""Short-lived, non-enrolling proof-of-key-possession pairing challenges."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base


class PiPairingAttempt(Base):
    __tablename__ = "pi_pairing_attempts"

    pairing_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    actor_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    hardware_id: Mapped[str] = mapped_column(String(128), nullable=False)
    public_key_b64: Mapped[str] = mapped_column(String(64), nullable=False)
    challenge_b64: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
