from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.orm.instruments import Instrument


async def get_by_symbol(session: AsyncSession, symbol: str) -> Instrument | None:
    result = await session.execute(select(Instrument).where(Instrument.symbol == symbol))
    return result.scalar_one_or_none()


async def get_all(session: AsyncSession) -> list[Instrument]:
    result = await session.execute(select(Instrument))
    return list(result.scalars().all())


async def get_by_id(session: AsyncSession, instrument_id: uuid.UUID) -> Instrument | None:
    result = await session.execute(select(Instrument).where(Instrument.id == instrument_id))
    return result.scalar_one_or_none()
