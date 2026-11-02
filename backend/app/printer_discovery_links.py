"""Permanent inventory identity returned by an authenticated Raspberry Pi.

Do not enable printer control through discovery records.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class PrinterDiscoveryLink(Base):
    __tablename__ = "printer_discovery_links"

    device_id: Mapped[str] = mapped_column(
        ForeignKey("devices.device_id"), primary_key=True
    )
    collector_id: Mapped[str] = mapped_column(
        ForeignKey("registered_collectors.collector_id"), nullable=False, index=True
    )
    manufacturer: Mapped[str | None] = mapped_column(String(100), nullable=True)
    serial_text: Mapped[str | None] = mapped_column(String(120), nullable=True)
    protocol: Mapped[str | None] = mapped_column(String(80), nullable=True)
    first_discovered: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_reported: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
