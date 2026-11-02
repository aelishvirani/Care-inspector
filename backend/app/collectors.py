"""Registered collector installations (Raspberry Pi or other approved hosts)."""
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base


class RegisteredCollector(Base):
    __tablename__ = "registered_collectors"

    collector_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    customer_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("customers.id"), nullable=True, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_seen: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
