from __future__ import annotations

import math
from datetime import datetime, date, timedelta, timezone

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

    # Fetch alt-data for xgboost from the eia + cot repos. The xgboost
    # placeholder treats either input as optional and falls back to price
    # momentum only when missing.
    latest_storage: dict | None = None
    latest_cot: dict | None = None
    try:
        from apps.api.adapters.registry import get_energy
        from apps.api.repos import eia as eia_repo
        from apps.api.repos import cot as cot_repo

        # Energy / storage alt-data path. NG has years of backfilled rows in
        # eia_storage_reports so we read from the table. CL has no backfill —
        # call EIAPetroleumAdapter live (24h-cached) for the latest weekly
        # Cushing stock report. Both paths emit the same {delta_vs_consensus,
        # actual_bcf} shape that xgboost consumes.
        if symbol.upper() == "CL":
            petroleum = get_energy("CL")
            live_storage = await petroleum.get_latest_storage()
            if live_storage and live_storage.get("surprise_bcf") is not None:
                latest_storage = {
                    "delta_vs_consensus": float(live_storage["surprise_bcf"]),
                    "actual_bcf": (
                        float(live_storage.get("actual_bcf"))
                        if live_storage.get("actual_bcf") is not None
                        else None
                    ),
                }
        else:
            storage_row = await eia_repo.get_latest(session)
            if storage_row is not None and storage_row.surprise_bcf is not None:
                # surprise_bcf = actual net_change - consensus → matches the
                # xgboost placeholder's "delta_vs_consensus" semantics.
                latest_storage = {
                    "delta_vs_consensus": float(storage_row.surprise_bcf),
                    "actual_bcf": float(storage_row.net_change_bcf)
                    if storage_row.net_change_bcf is not None
                    else None,
                }

        # Phase 14: filter COT reports to the active instrument's market code.
        # The instrument's metadata carries cftc_market_code (seeded in
        # instruments.json); fall back to no filter for pre-Phase-14 instruments.
        market_code = None
        if isinstance(instrument.metadata_, dict):
            market_code = instrument.metadata_.get("cftc_market_code") or None

        cot_recent = await cot_repo.get_recent(
            session, limit=2, cftc_contract_market_code=market_code
        )
        if len(cot_recent) >= 2:
            curr_net = cot_recent[0].managed_money_net
            prev_net = cot_recent[1].managed_money_net
            if curr_net is not None and prev_net is not None:
                latest_cot = {"mm_net_delta": float(curr_net - prev_net)}
    except Exception:
        # Defensive: alt-data lookup must never crash the signals path.
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
        "safety": safety_env.model_dump(mode="json"),
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

    # model_forecasts.generated_at is a TIMESTAMPTZ column → asyncpg returns
    # tz-aware datetimes. PriceBar.ts is a naive TIMESTAMP column. To avoid
    # mixed-tz comparisons (and the asyncpg-bind error on the bars query),
    # normalize every datetime in this function to naive UTC.
    def _naive_utc(dt: datetime) -> datetime:
        if dt.tzinfo is not None:
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt

    now = datetime.utcnow()
    rows = []
    for f in history:
        horizon_days = _HORIZON_DAYS.get(f.horizon, 1)
        generated_at_naive = _naive_utc(f.generated_at)
        horizon_end = generated_at_naive + timedelta(days=horizon_days)
        horizon_elapsed = horizon_end <= now

        # Look up realized price
        realized_pct: float | None = None
        if horizon_elapsed:
            # Get close at generated_at and at horizon_end
            start_bars = await price_repo.get_bars(
                session, contract_id, "1d",
                generated_at_naive - timedelta(days=1),
                generated_at_naive + timedelta(days=1),
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
