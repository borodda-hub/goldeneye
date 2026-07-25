import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.db.base import Base


class FuturesCurveVintage(Base):
    """One archived futures-curve snapshot per (vintage_date, symbol) — what
    the market adapter served ON that date. Immutable history: the repo is
    insert-only (Phase D2a); never update a past vintage."""

    __tablename__ = "futures_curve_vintages"
    __table_args__ = (
        UniqueConstraint("vintage_date", "symbol", name="uq_curve_vintage_date_symbol"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    vintage_date: Mapped[date] = mapped_column(Date, nullable=False)
    symbol: Mapped[str] = mapped_column(Text, nullable=False)
    curve: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
