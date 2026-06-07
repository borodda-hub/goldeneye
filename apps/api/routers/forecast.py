"""Forecast endpoints (Phase 30) — calibrated price-range forecasting.

`GET /v1/forecast/range` returns a symmetric expected-price range over a horizon
(empirically fat-tail-calibrated 80% and 95% bands — Phase 30c) plus the band's
*measured* walk-forward coverage — the honest track record, shown not asserted. Makes no
directional claim (direction is near-random per Phase 26; volatility is not).
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db.session import get_db
from apps.api.repos import contracts as contract_repo
from apps.api.repos import instruments as instr_repo
from apps.api.services.models.vol_range import (
    ESTIMATORS,
    forecast_vol_correlation,
    predict,
    walk_forward_coverage,
)
from apps.api.services.price_lookup import get_latest_closes
from apps.api.services.safety import wrap_with_uncertainty

router = APIRouter(prefix="/v1/forecast", tags=["forecast"])

_VALID_HORIZONS = ("1d", "1w", "1m")
_RANGE_CAVEATS = [
    "Range forecast only — no directional (up/down) claim is made.",
    "Both the 80% and 95% bands are calibrated with empirical fat-tail quantiles "
    "(returns are more extreme than a normal distribution); validated out-of-sample on "
    "~10y of real data across six commodities.",
    "Coverage shown is realized walk-forward over available history, not a guarantee.",
    "Use the band width, not the central vol level, as the estimate: the point-forecast "
    "vol level is not reliable out-of-sample (R² is negative). The band is what is "
    "calibrated.",
]


@router.get("/range")
async def get_range_forecast(
    symbol: str = Query(default="NG"),
    horizon: str = Query(default="1w"),
    estimator: str = Query(default="ewma"),
    session: AsyncSession = Depends(get_db),
) -> dict:
    if horizon not in _VALID_HORIZONS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported horizon {horizon!r}; supported: {list(_VALID_HORIZONS)}",
        )
    if estimator not in ESTIMATORS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported estimator {estimator!r}; supported: {list(ESTIMATORS)}",
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

    forecast = predict(closes, horizon, estimator)
    if forecast is None:
        raise HTTPException(
            status_code=422,
            detail="Insufficient price history for a range forecast (need ~30 closes).",
        )
    coverage = walk_forward_coverage(closes, horizon, estimator=estimator)
    fwd_vol_corr = forecast_vol_correlation(closes, horizon, estimator=estimator)

    caveats = list(_RANGE_CAVEATS)
    cov80 = coverage.get("cov80")
    cov95 = coverage.get("cov95")
    n_eff = coverage.get("n_eff") or 0
    if cov80 is not None:
        cov95_txt = f" / 95%: {cov95:.0%}" if cov95 is not None else ""
        caveats.append(
            f"Realized coverage on this series — 80%: {cov80:.0%}{cov95_txt} over "
            f"~{int(n_eff)} independent windows."
        )
    if fwd_vol_corr is not None:
        caveats.append(
            f"Forecast-vs-realized forward-vol correlation: {fwd_vol_corr:+.2f} "
            "(overlapping-window estimate; read the magnitude, not a t-stat)."
        )
    if estimator == "har_log":
        caveats.append(
            "Estimator: log-HAR — a richer vol model (daily/weekly/monthly realized "
            "variance) that beat the default EWMA on real out-of-sample point-forecast "
            "accuracy across six commodities. The calibrated band is what to trade off."
        )
    safety = wrap_with_uncertainty(
        forecast, confidence="medium", caveats=caveats, as_of=datetime.now(UTC)
    )

    return {
        "symbol": symbol,
        "horizon": horizon,
        "estimator": estimator,
        "range": asdict(forecast),
        "coverage": coverage,
        "forward_vol_corr": fwd_vol_corr,
        "safety": safety.model_dump(mode="json"),
    }
