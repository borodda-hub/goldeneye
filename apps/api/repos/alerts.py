from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.orm.alerts import Alert


async def get_unread(session: AsyncSession, limit: int = 50) -> list[Alert]:
    result = await session.execute(
        select(Alert).where(Alert.read.is_(False)).order_by(Alert.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


async def get_all(session: AsyncSession, limit: int = 50) -> list[Alert]:
    result = await session.execute(
        select(Alert).order_by(Alert.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


async def get_by_id(session: AsyncSession, alert_id: uuid.UUID) -> Alert | None:
    result = await session.execute(select(Alert).where(Alert.id == alert_id))
    return result.scalar_one_or_none()


async def acknowledge(session: AsyncSession, alert: Alert) -> Alert:
    alert.read = True  # type: ignore[assignment]
    alert.acknowledged = True  # type: ignore[assignment]
    await session.flush()
    return alert
