from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.orm.cot import COTReport

# Insertable columns (excludes id/fetched_at defaults and the GENERATED
# managed_money_net). Extra adapter keys are dropped at this boundary.
_UPSERT_COLUMNS = (
    "report_date",
    "release_date",
    "contract_market_name",
    "cftc_contract_market_code",
    "producer_long",
    "producer_short",
    "swap_long",
    "swap_short",
    "managed_money_long",
    "managed_money_short",
    "other_reportable_long",
    "other_reportable_short",
    "nonreportable_long",
    "nonreportable_short",
    "open_interest_total",
    "source",
)
# The table's UNIQUE constraint — the backfill's idempotency key.
_CONFLICT_KEY = ("report_date", "contract_market_name")
_CHUNK = 500


async def upsert_many(session: AsyncSession, rows: list[dict[str, Any]]) -> int:
    """Idempotent bulk upsert (Phase 31a backfill path; no commit — caller's
    transaction). ON CONFLICT (report_date, contract_market_name) DO UPDATE,
    so a re-run refreshes values instead of duplicating, and real history
    overwrites same-key mock rows."""
    if not rows:
        return 0
    cols = [c for c in _UPSERT_COLUMNS if c in rows[0]]
    affected = 0
    for i in range(0, len(rows), _CHUNK):
        chunk = [{c: r.get(c) for c in cols} for r in rows[i : i + _CHUNK]]
        stmt = pg_insert(COTReport).values(chunk)
        stmt = stmt.on_conflict_do_update(
            index_elements=list(_CONFLICT_KEY),
            set_={
                c: getattr(stmt.excluded, c) for c in cols if c not in _CONFLICT_KEY
            },
        )
        result = await session.execute(stmt)
        affected += result.rowcount or 0
    return affected


async def get_recent(
    session: AsyncSession,
    limit: int = 52,
    cftc_contract_market_code: str | None = None,
) -> list[COTReport]:
    """Recent COT reports, newest first.

    When ``cftc_contract_market_code`` is supplied, results are filtered to
    just that market — needed once the cot_reports table holds rows for
    multiple instruments (Phase 14+). Pre-Phase-14 callers pass ``None`` and
    get every row, preserving the original behavior.
    """
    stmt = select(COTReport).order_by(COTReport.report_date.desc()).limit(limit)
    if cftc_contract_market_code is not None:
        stmt = stmt.where(
            COTReport.cftc_contract_market_code == cftc_contract_market_code
        )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_latest(
    session: AsyncSession,
    cftc_contract_market_code: str | None = None,
) -> COTReport | None:
    stmt = select(COTReport).order_by(COTReport.report_date.desc()).limit(1)
    if cftc_contract_market_code is not None:
        stmt = stmt.where(
            COTReport.cftc_contract_market_code == cftc_contract_market_code
        )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
