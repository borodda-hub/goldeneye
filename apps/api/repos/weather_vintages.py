"""Insert-only repo for the weather-forecast vintage archive (Phase D5).

Vintages are immutable history — "what the adapter served on that date".
There is deliberately NO update path: `ON CONFLICT DO NOTHING` makes a
same-day re-tick a no-op instead of a rewrite (updating an archive of past
beliefs would be falsification, the exact failure mode vintage archives
exist to prevent).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.orm.weather_vintages import WeatherForecastVintage


async def insert_vintages(session: AsyncSession, rows: list[dict[str, Any]]) -> int:
    """Insert vintage rows; existing (vintage_date, region) rows are left
    untouched. Returns the number actually inserted."""
    if not rows:
        return 0
    stmt = pg_insert(WeatherForecastVintage).values(rows).on_conflict_do_nothing(
        index_elements=["vintage_date", "region"]
    )
    result = await session.execute(stmt)
    return result.rowcount or 0


async def count_vintage_days(session: AsyncSession, source: str | None = None) -> int:
    """Distinct archived days (optionally per source) — the validation
    re-entry trigger reads this (≥ ~180 real days spanning a winter)."""
    stmt = select(func.count(func.distinct(WeatherForecastVintage.vintage_date)))
    if source is not None:
        stmt = stmt.where(WeatherForecastVintage.source == source)
    return int((await session.execute(stmt)).scalar_one())
