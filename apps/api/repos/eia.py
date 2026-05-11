from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.orm.eia import EIAStorageReport


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
