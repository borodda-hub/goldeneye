"""Insert-only repo for the futures-curve vintage archive (Phase D2a).

Same doctrine as the weather archive (D5): vintages are immutable history —
ON CONFLICT DO NOTHING, never an update path. See repos/weather_vintages.py
for the rationale.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.orm.curve_vintages import FuturesCurveVintage


async def insert_vintages(session: AsyncSession, rows: list[dict[str, Any]]) -> int:
    """Insert curve vintage rows; existing (vintage_date, symbol) rows are
    left untouched. Returns the number actually inserted."""
    if not rows:
        return 0
    stmt = pg_insert(FuturesCurveVintage).values(rows).on_conflict_do_nothing(
        index_elements=["vintage_date", "symbol"]
    )
    result = await session.execute(stmt)
    return result.rowcount or 0


async def count_vintage_days(session: AsyncSession, source: str | None = None) -> int:
    """Distinct archived days — the D2 full-fidelity re-entry trigger reads
    this (≥ ~2y of daily curve vintages)."""
    stmt = select(func.count(func.distinct(FuturesCurveVintage.vintage_date)))
    if source is not None:
        stmt = stmt.where(FuturesCurveVintage.source == source)
    return int((await session.execute(stmt)).scalar_one())
