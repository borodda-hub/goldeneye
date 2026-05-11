from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.orm.prices import PriceBar, FuturesCurveSnapshot


async def get_bars(
    session: AsyncSession,
    contract_id: uuid.UUID,
    resolution: str,
    from_dt: datetime,
    to_dt: datetime,
    limit: int = 500,
) -> list[PriceBar]:
    result = await session.execute(
        select(PriceBar)
        .where(
            PriceBar.contract_id == contract_id,
            PriceBar.resolution == resolution,
            PriceBar.ts >= from_dt,
            PriceBar.ts <= to_dt,
        )
        .order_by(PriceBar.ts)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_latest(session: AsyncSession, contract_id: uuid.UUID, resolution: str = "1d") -> PriceBar | None:
    result = await session.execute(
        select(PriceBar)
        .where(PriceBar.contract_id == contract_id, PriceBar.resolution == resolution)
        .order_by(PriceBar.ts.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_latest_n_closes(
    session: AsyncSession, contract_id: uuid.UUID, n: int = 100, resolution: str = "1d"
) -> list[float]:
    result = await session.execute(
        select(PriceBar.close)
        .where(PriceBar.contract_id == contract_id, PriceBar.resolution == resolution)
        .order_by(PriceBar.ts.desc())
        .limit(n)
    )
    closes = [float(r) for r in result.scalars().all()]
    return list(reversed(closes))


async def get_latest_curve(
    session: AsyncSession, instrument_id: uuid.UUID
) -> FuturesCurveSnapshot | None:
    result = await session.execute(
        select(FuturesCurveSnapshot)
        .where(FuturesCurveSnapshot.instrument_id == instrument_id)
        .order_by(FuturesCurveSnapshot.ts.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
