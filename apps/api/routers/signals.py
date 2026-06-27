from __future__ import annotations

import math
from datetime import datetime, date, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.adapters.registry import get_market
from apps.api.db.session import get_db
from apps.api.repos import instruments as instr_repo
from apps.api.repos import contracts as contract_repo
from apps.api.repos import price_bars as price_repo
from apps.api.repos import forecasts as forecast_repo
from apps.api.services.price_lookup import get_latest_closes
from apps.api.services.model_registry import ForecastContext, run_all
from apps.api.services.ensemble import compute_ensemble, derive_envelope_confidence
from apps.api.services.model_calibration import model_weights_for
from apps.api.services.llm_explainer import explain_signal
from apps.api.services.asset_config import config_for
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
    closes = await get_latest_closes(
        session,
        contract_id=front.id if front else None,
        contract_code=front.contract_code if front else None,
        n=100,
    )

    # Fetch alt-data for the factor composite from the eia + cot repos. The
    # composite treats either input as optional and falls back to price
    # momentum only when missing.
    latest_storage: dict | None = None
    latest_cot: dict | None = None
    try:
        from apps.api.adapters.registry import get_energy
        from apps.api.repos import eia as eia_repo
        from apps.api.repos import cot as cot_repo

        # Energy / storage alt-data path. NG has years of backfilled rows in
        # eia_storage_reports so we read from the table. Non-NG instruments have
        # no backfill — ask the registry for the right per-symbol energy adapter:
        # EIA petroleum stocks (24h-cached) for CL/HO/RB, NullEnergyAdapter for
        # metals/other (returns None). Both live and table paths emit the same
        # {delta_vs_consensus, actual_bcf} shape that the composite consumes.
        if symbol.upper() == "NG":
            storage_row = await eia_repo.get_latest(session)
            if storage_row is not None and storage_row.surprise_bcf is not None:
                # surprise_bcf = actual net_change - consensus → matches the
                # factor composite's "delta_vs_consensus" semantics.
                latest_storage = {
                    "delta_vs_consensus": float(storage_row.surprise_bcf),
                    "actual_bcf": float(storage_row.net_change_bcf)
                    if storage_row.net_change_bcf is not None
                    else None,
                }
        else:
            energy = get_energy(symbol)
            live_storage = await energy.get_latest_storage()
            if live_storage and live_storage.get("surprise_bcf") is not None:
                latest_storage = {
                    "delta_vs_consensus": float(live_storage["surprise_bcf"]),
                    "actual_bcf": (
                        float(live_storage.get("actual_bcf"))
                        if live_storage.get("actual_bcf") is not None
                        else None
                    ),
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
        asset_class=getattr(instrument, "asset_class", "commodity"),
    )
    results = await run_all(ctx)
    weights = await model_weights_for(session, instrument.id, "1d")
    ensemble = compute_ensemble(results, model_weights=weights)

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
    _erange = ensemble.get("range") or {}
    _band_width = (
        _erange["high_pct"] - _erange["low_pct"]
        if _erange.get("high_pct") is not None and _erange.get("low_pct") is not None
        else None
    )
    env_conf = derive_envelope_confidence(
        ensemble_confidence=ensemble["confidence"],
        band_width=_band_width,
        band_cfg=ctx.cfg.ensemble_band,
    )
    explanation, safety_env = await explain_signal(
        signal_dict, ctx_dict, envelope_confidence=env_conf
    )

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

    # Pre-load daily closes once for the realized-pct lookup. Pulls from the
    # market adapter (same source /v1/chart/bars uses) so every symbol scores
    # regardless of whether its price_bars table is populated — only NGM26 is
    # seeded today, but the adapter has all front-months live from Yahoo.
    closes_by_date: dict[date, float] = {}
    if history and front is not None:
        oldest = min(_naive_utc(f.generated_at) for f in history)
        newest_horizon = max(
            _naive_utc(f.generated_at)
            + timedelta(days=_HORIZON_DAYS.get(f.horizon, 1))
            for f in history
        )
        try:
            market = get_market()
            adapter_bars = await market.get_bars(
                front.contract_code,
                "1d",
                from_dt=oldest - timedelta(days=2),
                to_dt=newest_horizon + timedelta(days=2),
            )
            for b in adapter_bars:
                ts = b.get("ts")
                close = b.get("close")
                if isinstance(ts, datetime) and close is not None:
                    closes_by_date[ts.date()] = float(close)
        except Exception:
            # Adapter unreachable — every row will fall back to "pending"
            # but the history still renders.
            closes_by_date = {}

    def _close_on_or_before(target: date) -> float | None:
        """Return the close for `target`, or the closest prior date (handles
        weekends + holidays). Bounded to a week-back search to avoid pulling
        in a price from a previous month."""
        for delta in range(0, 7):
            c = closes_by_date.get(target - timedelta(days=delta))
            if c is not None:
                return c
        return None

    now = datetime.utcnow()
    rows = []
    for f in history:
        horizon_days = _HORIZON_DAYS.get(f.horizon, 1)
        generated_at_naive = _naive_utc(f.generated_at)
        horizon_end = generated_at_naive + timedelta(days=horizon_days)
        horizon_elapsed = horizon_end <= now

        # Look up realized price from the pre-loaded close-by-date map.
        realized_pct: float | None = None
        if horizon_elapsed:
            start_close = _close_on_or_before(generated_at_naive.date())
            end_close = _close_on_or_before(horizon_end.date())
            if start_close is not None and end_close is not None and start_close > 0:
                realized_pct = (end_close / start_close) - 1.0

        score = score_forecast(
            direction=f.direction,
            horizon=f.horizon,
            expected_pct=float(f.expected_pct) if f.expected_pct is not None else None,
            realized_pct=realized_pct,
            # B5: per-asset-class deadband (commodity default == the prior 0.003).
            deadband=config_for(
                getattr(instrument, "asset_class", "commodity")
            ).default_deadband,
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
