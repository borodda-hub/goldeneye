from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.orm.cot import COTReport


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
