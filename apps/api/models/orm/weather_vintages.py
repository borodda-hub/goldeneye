import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, Numeric, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.db.base import Base


class WeatherForecastVintage(Base):
    """One archived weather forecast per (vintage_date, region) — what the
    configured adapter served ON that date. Immutable history: the repo is
    insert-only (Phase D5); never update a past vintage."""

    __tablename__ = "weather_forecast_vintages"
    __table_args__ = (
        UniqueConstraint(
            "vintage_date", "region", name="uq_weather_vintage_date_region"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    vintage_date: Mapped[date] = mapped_column(Date, nullable=False)
    region: Mapped[str] = mapped_column(Text, nullable=False)
    forecast: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    national_hdd_anomaly: Mapped[float | None] = mapped_column(Numeric)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
