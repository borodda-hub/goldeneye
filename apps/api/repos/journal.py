from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.orm.journal import UserDecisionJournal


async def create(session: AsyncSession, instrument_id: uuid.UUID, data: dict[str, Any]) -> UserDecisionJournal:
    entry = UserDecisionJournal(instrument_id=instrument_id, **data)
    session.add(entry)
    await session.flush()
    return entry


async def get_recent(session: AsyncSession, limit: int = 20) -> list[UserDecisionJournal]:
    result = await session.execute(
        select(UserDecisionJournal).order_by(UserDecisionJournal.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


async def get_by_id(session: AsyncSession, entry_id: uuid.UUID) -> UserDecisionJournal | None:
    result = await session.execute(
        select(UserDecisionJournal).where(UserDecisionJournal.id == entry_id)
    )
    return result.scalar_one_or_none()


async def update(session: AsyncSession, entry: UserDecisionJournal, patch: dict[str, Any]) -> UserDecisionJournal:
    for key, val in patch.items():
        setattr(entry, key, val)
    await session.flush()
    return entry
