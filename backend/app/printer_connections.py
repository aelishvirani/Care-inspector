from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class PrinterConnection(Base):
    __tablename__ = "printer_connections"

    device_id: Mapped[str] = mapped_column(
        ForeignKey("devices.device_id"),
        primary_key=True,
    )

    manufacturer: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    protocol: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="modbus_tcp",
    )

    host: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    port: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=502,
    )

    unit_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    collector_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
