from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.orm.contracts import Contract


async def get_front_month(session: AsyncSession, instrument_id: uuid.UUID) -> Contract | None:
    result = await session.execute(
        select(Contract)
        .where(Contract.instrument_id == instrument_id, Contract.is_front_month.is_(True))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_by_code(session: AsyncSession, contract_code: str) -> Contract | None:
    result = await session.execute(
        select(Contract).where(Contract.contract_code == contract_code)
    )
    return result.scalar_one_or_none()


async def list_for_instrument(session: AsyncSession, instrument_id: uuid.UUID) -> list[Contract]:
    result = await session.execute(
        select(Contract).where(Contract.instrument_id == instrument_id).order_by(Contract.expiry_date)
    )
    return list(result.scalars().all())
