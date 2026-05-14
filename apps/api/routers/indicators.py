"""Chart indicators endpoint (Phase 15 step 15b).

GET /v1/chart/indicators?symbol=NG&spec=ema:21,sma:50,hma:21&from=...&to=...

Spec syntax: comma-separated `type:period[:source]` items, e.g.
`ema:21:close`. Unknown types and unknown sources yield 400. VWMA on an
instrument without volume data yields 400.

OHLCV is pulled via repos/price_bars from the front-month contract for the
given symbol. Each indicator is dispatched through the Redis-cached compute
wrapper from services/indicators/cache so repeat requests serve from cache.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db.session import get_db
from apps.api.repos import contracts as contract_repo
from apps.api.repos import instruments as instr_repo
from apps.api.repos import price_bars as price_bars_repo
from apps.api.services.indicators import (
    IndicatorSeries,
    IndicatorSpec,
    UnknownIndicatorError,
    VolumeRequiredError,
    registered_types,
)
from apps.api.services.indicators.cache import cached_compute


class GetIndicatorsResponse(BaseModel):
    symbol: str
    indicators: list[IndicatorSeries]

router = APIRouter(prefix="/v1/chart", tags=["chart"])

_RESOLUTION = "1d"
_DEFAULT_WINDOW_DAYS = 365
_MIN_PERIOD = 2
_MAX_PERIOD = 500


def _parse_spec(spec: str) -> list[IndicatorSpec]:
    """Parse `ema:21,sma:50:hl2,vwma:20` into a list of IndicatorSpec."""
    supported = set(registered_types())
    out: list[IndicatorSpec] = []
    for item in spec.split(","):
        s = item.strip()
        if not s:
            continue
        parts = s.split(":")
        type_key = parts[0].strip().lower()
        if type_key not in supported:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"unknown indicator type {type_key!r}; "
                    f"supported: {sorted(supported)}"
                ),
            )
        try:
            period = int(parts[1]) if len(parts) > 1 else 20
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"bad period in {s!r}: {e}")
        if not (_MIN_PERIOD <= period <= _MAX_PERIOD):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"period out of range in {s!r}: {period} "
                    f"(allowed {_MIN_PERIOD}..{_MAX_PERIOD})"
                ),
            )
        source = parts[2].strip().lower() if len(parts) > 2 else "close"
        out.append(
            IndicatorSpec(type=type_key, params={"period": period, "source": source})
        )
    if not out:
        raise HTTPException(status_code=400, detail="spec is empty")
    return out


@router.get("/indicators", response_model=GetIndicatorsResponse)
async def get_indicators(
    symbol: str = Query(..., description="Instrument symbol, e.g. NG or CL"),
    spec: str = Query(
        ...,
        description="Comma-separated `type:period[:source]` items, e.g. ema:21,sma:50",
    ),
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    specs = _parse_spec(spec)

    now = datetime.now(UTC).replace(tzinfo=None)
    to_dt = to if to is not None else now
    from_dt = from_ if from_ is not None else (to_dt - timedelta(days=_DEFAULT_WINDOW_DAYS))
    if to_dt.tzinfo is not None:
        to_dt = to_dt.replace(tzinfo=None)
    if from_dt.tzinfo is not None:
        from_dt = from_dt.replace(tzinfo=None)

    instrument = await instr_repo.get_by_symbol(session, symbol)
    if instrument is None:
        raise HTTPException(status_code=404, detail=f"unknown symbol {symbol!r}")

    contract = await contract_repo.get_front_month(session, instrument.id)
    if contract is None:
        raise HTTPException(
            status_code=404, detail=f"no front-month contract for {symbol!r}"
        )

    bars = await price_bars_repo.get_bars(
        session, contract.id, _RESOLUTION, from_dt, to_dt, limit=10000
    )
    if not bars:
        return {"symbol": symbol, "indicators": []}

    df = pd.DataFrame(
        {
            "open": [float(b.open) for b in bars],
            "high": [float(b.high) for b in bars],
            "low": [float(b.low) for b in bars],
            "close": [float(b.close) for b in bars],
            "volume": [
                float(b.volume) if b.volume is not None else None for b in bars
            ],
        },
        index=pd.DatetimeIndex([b.ts for b in bars]),
    )

    indicators_payload: list[dict[str, Any]] = []
    for ind_spec in specs:
        try:
            series = await cached_compute(
                ind_spec, df, symbol=symbol, from_ts=from_dt, to_ts=to_dt
            )
        except UnknownIndicatorError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except VolumeRequiredError as e:
            raise HTTPException(status_code=400, detail=str(e))
        indicators_payload.append(series.model_dump(mode="json"))

    return {"symbol": symbol, "indicators": indicators_payload}
