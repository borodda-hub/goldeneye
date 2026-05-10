import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Enum, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.db.base import Base


class PriceBar(Base):
    __tablename__ = "price_bars"

    ts: Mapped[datetime] = mapped_column(primary_key=True)
    contract_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contracts.id"), primary_key=True)
    resolution: Mapped[str] = mapped_column(
        Enum("1m", "5m", "15m", "1h", "1d", name="bar_resolution_t"), primary_key=True
    )
    open: Mapped[float] = mapped_column(Numeric, nullable=False)
    high: Mapped[float] = mapped_column(Numeric, nullable=False)
    low: Mapped[float] = mapped_column(Numeric, nullable=False)
    close: Mapped[float] = mapped_column(Numeric, nullable=False)
    volume: Mapped[int | None] = mapped_column(BigInteger)
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default="mock")


class TickData(Base):
    __tablename__ = "tick_data"

    ts: Mapped[datetime] = mapped_column(primary_key=True)
    contract_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contracts.id"), primary_key=True)
    price: Mapped[float] = mapped_column(Numeric, nullable=False)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    side: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default="mock")


class FuturesCurveSnapshot(Base):
    __tablename__ = "futures_curve_snapshots"

    ts: Mapped[datetime] = mapped_column(primary_key=True)
    instrument_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("instruments.id"), primary_key=True)
    curve: Mapped[list] = mapped_column(JSONB, nullable=False)
