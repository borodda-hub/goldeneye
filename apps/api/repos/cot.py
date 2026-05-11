from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.orm.cot import COTReport


async def get_recent(session: AsyncSession, limit: int = 52) -> list[COTReport]:
    result = await session.execute(
        select(COTReport).order_by(COTReport.report_date.desc()).limit(limit)
    )
    return list(result.scalars().all())


async def get_latest(session: AsyncSession) -> COTReport | None:
    result = await session.execute(
        select(COTReport).order_by(COTReport.report_date.desc()).limit(1)
    )
    return result.scalar_one_or_none()
