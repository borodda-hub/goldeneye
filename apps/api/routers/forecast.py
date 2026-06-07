"""Forecast endpoints (Phase 30) — calibrated price-range forecasting.

`GET /v1/forecast/range` returns a symmetric expected-price range over a horizon (the
calibrated 80% band + a reported 95% band) plus the band's *measured* walk-forward
coverage — the honest track record, shown not asserted. Makes no directional claim
(direction is near-random per Phase 26; volatility is not).
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db.session import get_db
from apps.api.repos import contracts as contract_repo
from apps.api.repos import instruments as instr_repo
from apps.api.services.models.vol_range import predict, walk_forward_coverage
from apps.api.services.price_lookup import get_latest_closes
from apps.api.services.safety import wrap_with_uncertainty

router = APIRouter(prefix="/v1/forecast", tags=["forecast"])

_VALID_HORIZONS = ("1d", "1w", "1m")
_RANGE_CAVEATS = [
    "Range forecast only — no directional (up/down) claim is made.",
    "The 80% band is the calibrated surface; the 95% band runs light due to fat tails "
    "(returns are more extreme than a normal distribution).",
    "Coverage shown is realized walk-forward over available history, not a guarantee.",
]


@router.get("/range")
async def get_range_forecast(
    symbol: str = Query(default="NG"),
    horizon: str = Query(default="1w"),
    session: AsyncSession = Depends(get_db),
) -> dict:
    if horizon not in _VALID_HORIZONS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported horizon {horizon!r}; supported: {list(_VALID_HORIZONS)}",
        )
    instrument = await instr_repo.get_by_symbol(session, symbol)
    if instrument is None:
        raise HTTPException(status_code=404, detail=f"Instrument {symbol!r} not found")

    front = await contract_repo.get_front_month(session, instrument.id)
    closes = await get_latest_closes(
        session,
        contract_id=front.id if front else None,
        contract_code=front.contract_code if front else None,
        n=250,
    )

    forecast = predict(closes, horizon)
    if forecast is None:
        raise HTTPException(
            status_code=422,
            detail="Insufficient price history for a range forecast (need ~30 closes).",
        )
    coverage = walk_forward_coverage(closes, horizon)

    caveats = list(_RANGE_CAVEATS)
    cov80 = coverage.get("cov80")
    if cov80 is not None:
        caveats.append(f"Realized 80% coverage on this series: {cov80:.0%}.")
    safety = wrap_with_uncertainty(
        forecast, confidence="medium", caveats=caveats, as_of=datetime.now(UTC)
    )

    return {
        "symbol": symbol,
        "horizon": horizon,
        "range": asdict(forecast),
        "coverage": coverage,
        "safety": safety.model_dump(mode="json"),
    }
