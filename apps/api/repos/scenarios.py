from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.orm.scenarios import ScenarioRun


async def create(session: AsyncSession, instrument_id: uuid.UUID, name: str, shocks: list, result: dict) -> ScenarioRun:
    run = ScenarioRun(instrument_id=instrument_id, name=name, shocks=shocks, result=result)
    session.add(run)
    await session.flush()
    return run


async def get_recent(session: AsyncSession, limit: int = 20) -> list[ScenarioRun]:
    result = await session.execute(
        select(ScenarioRun).order_by(ScenarioRun.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


async def get_by_id(session: AsyncSession, run_id: uuid.UUID) -> ScenarioRun | None:
    result = await session.execute(select(ScenarioRun).where(ScenarioRun.id == run_id))
    return result.scalar_one_or_none()
