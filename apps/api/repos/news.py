from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.orm.news import NewsEvent


async def get_recent(session: AsyncSession, limit: int = 20) -> list[NewsEvent]:
    result = await session.execute(
        select(NewsEvent).order_by(NewsEvent.published_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


async def get_by_category(session: AsyncSession, category: str, limit: int = 10) -> list[NewsEvent]:
    result = await session.execute(
        select(NewsEvent)
        .where(NewsEvent.category == category)
        .order_by(NewsEvent.published_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())
