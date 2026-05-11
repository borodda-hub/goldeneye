from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.orm.forecasts import ModelForecast


async def create(
    session: AsyncSession,
    instrument_id: uuid.UUID,
    model_name: str,
    horizon: str,
    direction: str,
    confidence: str,
    supporting: list,
    contradicting: list,
    expected_pct: float | None = None,
    range_low_pct: float | None = None,
    range_high_pct: float | None = None,
    vol_regime: str | None = None,
) -> ModelForecast:
    forecast = ModelForecast(
        instrument_id=instrument_id,
        model_name=model_name,
        horizon=horizon,
        direction=direction,
        confidence=confidence,
        supporting=supporting,
        contradicting=contradicting,
        expected_pct=expected_pct,
        range_low_pct=range_low_pct,
        range_high_pct=range_high_pct,
        vol_regime=vol_regime,
    )
    session.add(forecast)
    await session.flush()
    return forecast


async def get_history(
    session: AsyncSession,
    instrument_id: uuid.UUID,
    from_dt: datetime,
    to_dt: datetime,
    model: str | None = None,
    limit: int = 200,
) -> list[ModelForecast]:
    q = (
        select(ModelForecast)
        .where(
            ModelForecast.instrument_id == instrument_id,
            ModelForecast.generated_at >= from_dt,
            ModelForecast.generated_at <= to_dt,
        )
        .order_by(ModelForecast.generated_at.desc())
        .limit(limit)
    )
    if model:
        q = q.where(ModelForecast.model_name == model)
    result = await session.execute(q)
    return list(result.scalars().all())
