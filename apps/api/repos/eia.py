from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.orm.eia import EIAStorageReport

# Insertable columns (excludes id/fetched_at defaults). Extra adapter keys
# (e.g. the petroleum shape's actual_bcf) are dropped at this boundary.
_UPSERT_COLUMNS = (
    "report_date",
    "week_ending",
    "total_lower_48_bcf",
    "east_bcf",
    "midwest_bcf",
    "mountain_bcf",
    "pacific_bcf",
    "south_central_bcf",
    "net_change_bcf",
    "five_year_avg_bcf",
    "five_year_max_bcf",
    "five_year_min_bcf",
    "consensus_estimate",
    "surprise_bcf",
    "source",
)
# report_date is UNIQUE — the backfill's idempotency key. NG national storage
# only: one series, one row per publication date (see backtest._storage_as_of).
_CONFLICT_KEY = ("report_date",)
_CHUNK = 500


async def upsert_many(session: AsyncSession, rows: list[dict[str, Any]]) -> int:
    """Idempotent bulk upsert (Phase 31a backfill path; no commit — caller's
    transaction). ON CONFLICT (report_date) DO UPDATE, so a re-run refreshes
    values instead of duplicating, and real history overwrites same-key mock
    rows."""
    if not rows:
        return 0
    cols = [c for c in _UPSERT_COLUMNS if c in rows[0]]
    affected = 0
    for i in range(0, len(rows), _CHUNK):
        chunk = [{c: r.get(c) for c in cols} for r in rows[i : i + _CHUNK]]
        stmt = pg_insert(EIAStorageReport).values(chunk)
        stmt = stmt.on_conflict_do_update(
            index_elements=list(_CONFLICT_KEY),
            set_={
                c: getattr(stmt.excluded, c) for c in cols if c not in _CONFLICT_KEY
            },
        )
        result = await session.execute(stmt)
        affected += result.rowcount or 0
    return affected


async def get_recent(session: AsyncSession, limit: int = 100) -> list[EIAStorageReport]:
    result = await session.execute(
        select(EIAStorageReport).order_by(EIAStorageReport.report_date.desc()).limit(limit)
    )
    return list(result.scalars().all())


async def get_latest(session: AsyncSession) -> EIAStorageReport | None:
    result = await session.execute(
        select(EIAStorageReport).order_by(EIAStorageReport.report_date.desc()).limit(1)
    )
    return result.scalar_one_or_none()
