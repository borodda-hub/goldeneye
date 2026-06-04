"""Chart indicators endpoint (Phase 15 step 15b).

GET /v1/chart/indicators?symbol=NG&spec=ema:21,sma:50,hma:21&from=...&to=...

Spec syntax: comma-separated `type:period[:source]` items, e.g.
`ema:21:close`. Unknown types and unknown sources yield 400. VWMA on an
instrument without volume data yields 400.

OHLCV is pulled through the registered market adapter (same source the
`/v1/chart/bars` endpoint uses), so indicator lines stay aligned to the
candlesticks the chart actually renders — for any contract, with or
without seeded historical data. Each indicator dispatches through the
Redis-cached compute wrapper in services/indicators/cache.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.adapters.registry import get_market
from apps.api.db.session import get_db
from apps.api.repos import contracts as contract_repo
from apps.api.repos import instruments as instr_repo
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

# Moving averages keep the original `type:period[:source]` grammar.
_MA_TYPES = {"sma", "ema", "wma", "hma", "dema", "tema", "vwma"}

# Oscillators / bands: positional numeric params (name, default). `stddev`/
# `mult` may be fractional; period-like params are coerced to int + range-checked.
_PARAM_SCHEMA: dict[str, list[tuple[str, float]]] = {
    "rsi": [("period", 14)],
    "macd": [("fast", 12), ("slow", 26), ("signal", 9)],
    "stoch": [("k", 14), ("d", 3), ("smooth", 3)],
    "adx": [("period", 14)],
    "atr": [("period", 14)],
    "bb": [("period", 20), ("stddev", 2)],
    "kc": [("period", 20), ("mult", 2)],
    "dc": [("period", 20)],
}
_PERIODIC_KEYS = {"period", "fast", "slow", "signal", "k", "d", "smooth"}


def _parse_spec(spec: str) -> list[IndicatorSpec]:
    """Parse `ema:21,sma:50:hl2,macd:12:26:9,bb:20:2` into IndicatorSpec list."""
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
        if type_key in _MA_TYPES:
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
                IndicatorSpec(
                    type=type_key, params={"period": period, "source": source}
                )
            )
        else:
            schema = _PARAM_SCHEMA.get(type_key, [("period", 20)])
            params: dict[str, Any] = {}
            for i, (name, default) in enumerate(schema):
                raw = parts[i + 1].strip() if len(parts) > i + 1 and parts[i + 1].strip() else None
                try:
                    val: float = float(raw) if raw is not None else float(default)
                except ValueError as e:
                    raise HTTPException(status_code=400, detail=f"bad {name} in {s!r}: {e}")
                if name in _PERIODIC_KEYS:
                    iv = int(val)
                    if not (1 <= iv <= _MAX_PERIOD):
                        raise HTTPException(
                            status_code=400,
                            detail=f"{name} out of range in {s!r}: {iv} (1..{_MAX_PERIOD})",
                        )
                    params[name] = iv
                else:
                    params[name] = val
            out.append(IndicatorSpec(type=type_key, params=params))
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

    market = get_market()
    bars = await market.get_bars(
        contract.contract_code, _RESOLUTION, from_dt=from_dt, to_dt=to_dt
    )
    if not bars:
        return {"symbol": symbol, "indicators": []}

    df = pd.DataFrame(
        {
            "open": [float(b["open"]) for b in bars],
            "high": [float(b["high"]) for b in bars],
            "low": [float(b["low"]) for b in bars],
            "close": [float(b["close"]) for b in bars],
            "volume": [
                float(b["volume"]) if b.get("volume") is not None else None
                for b in bars
            ],
        },
        index=pd.DatetimeIndex([b["ts"] for b in bars]),
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
