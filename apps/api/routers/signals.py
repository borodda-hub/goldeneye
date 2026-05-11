from __future__ import annotations

import math
from datetime import datetime, date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db.session import get_db
from apps.api.repos import instruments as instr_repo
from apps.api.repos import contracts as contract_repo
from apps.api.repos import price_bars as price_repo
from apps.api.repos import forecasts as forecast_repo
from apps.api.services.model_registry import ForecastContext, run_all
from apps.api.services.ensemble import compute_ensemble
from apps.api.services.llm_explainer import explain_signal
from apps.api.services.signal_scoring import score_forecast

router = APIRouter(prefix="/v1/signals", tags=["signals"])

_HORIZON_DAYS = {"1d": 1, "1w": 7, "1m": 30}


@router.get("/current")
async def get_current_signal(
    symbol: str = Query(default="NG"),
    session: AsyncSession = Depends(get_db),
) -> dict:
    instrument = await instr_repo.get_by_symbol(session, symbol)
    if instrument is None:
        raise HTTPException(status_code=404, detail=f"Instrument {symbol!r} not found")

    front = await contract_repo.get_front_month(session, instrument.id)
    closes = await price_repo.get_latest_n_closes(
        session, front.id if front else instrument.id, n=100
    )

    # Fetch alt-data for xgboost
    # These repos may not exist yet; use try/except to gracefully degrade
    latest_storage: dict | None = None
    latest_cot: dict | None = None
    try:
        from apps.api.repos import energy_data as energy_repo  # type: ignore[import]
        storage_row = await energy_repo.get_latest_storage(session, symbol)
        if storage_row is not None:
            latest_storage = {
                "delta_vs_consensus": float(storage_row.delta_vs_consensus)
                if storage_row.delta_vs_consensus is not None else 0.0,
                "actual_bcf": float(storage_row.actual_bcf) if storage_row.actual_bcf is not None else None,
            }
    except (ImportError, AttributeError, Exception):
        pass

    try:
        from apps.api.repos import positioning_data as pos_repo  # type: ignore[import]
        cot_row = await pos_repo.get_latest_cot(session, symbol)
        if cot_row is not None:
            latest_cot = {
                "mm_net_delta": float(cot_row.mm_net_delta)
                if cot_row.mm_net_delta is not None else 0.0,
            }
    except (ImportError, AttributeError, Exception):
        pass

    ctx = ForecastContext(
        symbol=symbol,
        closes=closes,
        latest_storage=latest_storage,
        latest_cot=latest_cot,
    )
    results = await run_all(ctx)
    ensemble = compute_ensemble(results)

    models_out = []
    for r in results:
        models_out.append({
            "model_name": r.model_name,
            "horizon": r.horizon,
            "direction": r.direction,
            "confidence": r.confidence,
            "expected_pct": r.expected_pct,
            "inputs_used": getattr(r, "inputs_used", ["closes"]),
            "range": {
                "low_pct": r.range_low_pct,
                "high_pct": r.range_high_pct,
            },
            "supporting": r.supporting,
            "contradicting": r.contradicting,
        })

    signal_dict = {
        "direction": ensemble["direction"],
        "confidence": ensemble["confidence"],
        "vol_regime": ensemble.get("vol_regime"),
        "agreement": ensemble.get("agreement"),
        "confidence_rationale": ensemble.get("confidence_rationale"),
        "models": models_out,
    }
    ctx_dict = {
        "symbol": symbol,
        "closes_count": len(closes),
        "storage": latest_storage,
        "cot": latest_cot,
        "models": models_out,
    }
    explanation, safety_env = await explain_signal(signal_dict, ctx_dict)

    return {
        "instrument": symbol,
        "ensemble": {
            "direction": ensemble["direction"],
            "confidence": ensemble["confidence"],
            "vol_regime": ensemble.get("vol_regime"),
            "expected_pct": ensemble.get("expected_pct"),
            "range": ensemble.get("range"),
            "agreement": ensemble.get("agreement"),
            "confidence_rationale": ensemble.get("confidence_rationale"),
            "caveats": ensemble.get("caveats", []),
        },
        "models": models_out,
        "explanation": explanation,
        "safety": safety_env.model_dump(),
    }


@router.get("/history")
async def get_signal_history(
    symbol: str = Query(default="NG"),
    from_: date = Query(default=date(2026, 1, 1), alias="from"),
    to: date = Query(default_factory=date.today),
    model: str | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=500),
    status: str = Query(default="scored"),  # "all" | "scored" | "pending"
    session: AsyncSession = Depends(get_db),
) -> dict:
    instrument = await instr_repo.get_by_symbol(session, symbol)
    if instrument is None:
        raise HTTPException(status_code=404, detail=f"Instrument {symbol!r} not found")

    front = await contract_repo.get_front_month(session, instrument.id)
    contract_id = front.id if front else instrument.id

    from_dt = datetime(from_.year, from_.month, from_.day)
    to_dt = datetime(to.year, to.month, to.day, 23, 59, 59)

    history = await forecast_repo.get_history(
        session, instrument.id, from_dt, to_dt, model=model, limit=limit * 4
    )

    now = datetime.utcnow()
    rows = []
    for f in history:
        horizon_days = _HORIZON_DAYS.get(f.horizon, 1)
        horizon_end = f.generated_at + timedelta(days=horizon_days)
        horizon_elapsed = horizon_end <= now

        # Look up realized price
        realized_pct: float | None = None
        if horizon_elapsed:
            # Get close at generated_at and at horizon_end
            start_bars = await price_repo.get_bars(
                session, contract_id, "1d",
                f.generated_at - timedelta(days=1),
                f.generated_at + timedelta(days=1),
                limit=2,
            )
            end_bars = await price_repo.get_bars(
                session, contract_id, "1d",
                horizon_end - timedelta(days=1),
                horizon_end + timedelta(days=1),
                limit=2,
            )
            if start_bars and end_bars:
                start_close = float(start_bars[-1].close)
                end_close = float(end_bars[-1].close)
                if start_close > 0:
                    realized_pct = (end_close / start_close) - 1.0

        score = score_forecast(
            direction=f.direction,
            horizon=f.horizon,
            expected_pct=float(f.expected_pct) if f.expected_pct is not None else None,
            realized_pct=realized_pct,
        )

        outcome = score["outcome"]
        if status == "scored" and outcome in ("pending",):
            continue
        if status == "pending" and outcome != "pending":
            continue

        rows.append({
            "id": str(f.id),
            "generated_at": f.generated_at.isoformat(),
            "horizon_end": horizon_end.isoformat() + "Z",
            "model_name": f.model_name,
            "horizon": f.horizon,
            "direction": f.direction,
            "confidence": f.confidence,
            "expected_pct": float(f.expected_pct) if f.expected_pct is not None else None,
            "vol_regime": f.vol_regime,
            "outcome": outcome,
            "realized_pct": score["realized_pct"],
            "delta_from_expected_pct": score["delta_from_expected_pct"],
            "scored_at": horizon_end.isoformat() + "Z" if horizon_elapsed else None,
        })

        if len(rows) >= limit:
            break

    # Sort by horizon_end desc
    rows.sort(key=lambda r: r["horizon_end"], reverse=True)

    return {"instrument": symbol, "rows": rows}
