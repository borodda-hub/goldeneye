from __future__ import annotations

from datetime import datetime, date

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

router = APIRouter(prefix="/v1/signals", tags=["signals"])


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

    ctx = ForecastContext(symbol=symbol, closes=closes)
    results = await run_all(ctx)
    ensemble = compute_ensemble(results)

    signal_dict = {
        "direction": ensemble["direction"],
        "confidence": ensemble["confidence"],
        "vol_regime": ensemble.get("vol_regime"),
    }
    ctx_dict = {"symbol": symbol, "closes_count": len(closes)}
    explanation, safety_env = await explain_signal(signal_dict, ctx_dict)

    models_out = []
    for r in results:
        models_out.append({
            "name": r.model_name,
            "horizon": r.horizon,
            "direction": r.direction,
            "confidence": r.confidence,
            "expected_pct": r.expected_pct,
            "range": {
                "low_pct": r.range_low_pct,
                "high_pct": r.range_high_pct,
            },
            "supporting": r.supporting,
            "contradicting": r.contradicting,
        })

    return {
        "instrument": symbol,
        "ensemble": {
            "direction": ensemble["direction"],
            "confidence": ensemble["confidence"],
            "vol_regime": ensemble.get("vol_regime"),
            "expected_pct": ensemble.get("expected_pct"),
            "range": ensemble.get("range"),
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
    session: AsyncSession = Depends(get_db),
) -> dict:
    instrument = await instr_repo.get_by_symbol(session, symbol)
    if instrument is None:
        raise HTTPException(status_code=404, detail=f"Instrument {symbol!r} not found")

    from_dt = datetime(from_.year, from_.month, from_.day)
    to_dt = datetime(to.year, to.month, to.day, 23, 59, 59)

    history = await forecast_repo.get_history(session, instrument.id, from_dt, to_dt, model=model)

    rows = [
        {
            "id": str(f.id),
            "generated_at": f.generated_at.isoformat(),
            "model_name": f.model_name,
            "horizon": f.horizon,
            "direction": f.direction,
            "confidence": f.confidence,
            "expected_pct": float(f.expected_pct) if f.expected_pct is not None else None,
            "vol_regime": f.vol_regime,
        }
        for f in history
    ]

    return {"instrument": symbol, "rows": rows}
