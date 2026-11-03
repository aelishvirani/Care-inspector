"""One-time cloud key-auth challenges for already registered Raspberry Pis."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base


class PiCloudChallenge(Base):
    __tablename__ = "pi_cloud_challenges"
    challenge_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    hardware_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("pi_registered_devices.hardware_id"),
        nullable=False, index=True
    )
    nonce_b64: Mapped[str] = mapped_column(String(44), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
