"""Backtest endpoint — runs the replay engine and optionally persists results.

The Signal Lab's "Backtest" UI section (Phase 10 step 4) drives this. The
endpoint is intentionally synchronous: a 90-day NG 1d backtest completes
in a few hundred ms against the seeded fixtures, well inside the
TanStack-Query patience window. Longer windows or expensive models may
need a job-queued variant later.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db.session import get_db
from apps.api.models.orm.forecasts import ModelForecast
from apps.api.repos import instruments as instr_repo
from apps.api.services.backtest import (
    BACKTEST_SOURCE_MARKER,
    BacktestConfig,
    SUPPORTED_MODELS,
    persist_backtest_rows,
    run_backtest,
)

router = APIRouter(prefix="/v1/backtest", tags=["backtest"])

# Default window: last 90 days. Matches the depth the synthetic seed
# produced so the UI's history table looks visually similar after the
# swap — just with honest numbers.
_DEFAULT_WINDOW_DAYS = 90
_SUPPORTED_HORIZONS = frozenset({"1d", "1w", "1m"})


def _row_to_json(row: Any) -> dict[str, Any]:
    """BacktestRow → JSON-serializable dict. datetime → ISO string."""
    d = asdict(row)
    if d.get("generated_at") is not None:
        d["generated_at"] = d["generated_at"].isoformat()
    return d


@router.get("")
async def run_backtest_endpoint(
    model: str = Query(..., description="Forecasting model name"),
    symbol: str = Query("NG"),
    from_: date | None = Query(None, alias="from"),
    to: date | None = Query(None),
    horizon: str = Query("1d"),
    retrain_days: int | None = Query(None, ge=1, le=180),
    persist: bool = Query(True, description="Write results to model_forecasts"),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Run a backtest and (optionally) persist forecasts to model_forecasts.

    Validation:
      400 — unknown model, unsupported horizon, or reversed date range.
      404 — symbol not found in `instruments`.

    Persistence:
      When `persist=true` (default), backtest rows replace any existing
      rows for the same (instrument, model, horizon) that fall inside the
      backtest's `generated_at` range. They also clear synthetic seed rows
      (inputs_hash IS NULL) for the same model so the Signal Lab history
      doesn't mix fake + real outcomes.
    """
    if model not in SUPPORTED_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown model {model!r}; supported: {sorted(SUPPORTED_MODELS)}",
        )
    if horizon not in _SUPPORTED_HORIZONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported horizon {horizon!r}; supported: {sorted(_SUPPORTED_HORIZONS)}",
        )

    today = date.today()
    to_date = to or today
    from_date = from_ or (to_date - timedelta(days=_DEFAULT_WINDOW_DAYS))
    if from_date > to_date:
        raise HTTPException(
            status_code=400,
            detail=f"from ({from_date}) must be on or before to ({to_date})",
        )

    instrument = await instr_repo.get_by_symbol(session, symbol)
    if instrument is None:
        raise HTTPException(status_code=404, detail=f"Instrument {symbol!r} not found")

    config = BacktestConfig(
        model_name=model,
        symbol=symbol,
        from_date=from_date,
        to_date=to_date,
        horizon=horizon,
        retrain_cadence_days=retrain_days,
    )

    rows, summary = await run_backtest(session, config)

    inserted = 0
    if persist and rows:
        inserted = await persist_backtest_rows(
            session,
            instrument_id=instrument.id,
            rows=rows,
            config=config,
        )
        await session.commit()

    return {
        "config": {
            "model": config.model_name,
            "symbol": config.symbol,
            "from": config.from_date.isoformat(),
            "to": config.to_date.isoformat(),
            "horizon": config.horizon,
            "retrain_cadence_days": config.retrain_cadence_days,
            "persisted": persist,
            "rows_inserted": inserted,
        },
        "summary": asdict(summary),
        "rows": [_row_to_json(r) for r in rows],
    }


@router.get("/summary")
async def backtest_summary(
    symbol: str = Query("NG"),
    horizon: str = Query("1d"),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Per-model aggregate over persisted backtest rows.

    Pure SQL aggregate against model_forecasts where inputs_hash =
    BACKTEST_SOURCE_MARKER. Reads the `features` JSONB column for the
    `outcome` field that persist_backtest_rows wrote at backtest time —
    no re-scoring, no model loop, no price-bar lookups.

    Response shape mirrors what the Signal Lab Backtest card renders:
      {
        "models": [
          {"name": "...", "scored": int, "n": int, "hit_rate": float,
           "last_generated_at": iso | null, "from_date": iso | null,
           "to_date": iso | null},
          ...
        ]
      }
    """
    if horizon not in _SUPPORTED_HORIZONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported horizon {horizon!r}; supported: {sorted(_SUPPORTED_HORIZONS)}",
        )

    instrument = await instr_repo.get_by_symbol(session, symbol)
    if instrument is None:
        raise HTTPException(status_code=404, detail=f"Instrument {symbol!r} not found")

    # The features column carries {"realized_pct", "outcome", ...}. Cast the
    # outcome key to text and aggregate hits + scored counts per model.
    outcome_expr = ModelForecast.features["outcome"].astext
    hit_count = func.count(outcome_expr).filter(outcome_expr == "hit")
    miss_count = func.count(outcome_expr).filter(outcome_expr == "miss")
    indet_count = func.count(outcome_expr).filter(outcome_expr == "indeterminate")
    pending_count = func.count(outcome_expr).filter(outcome_expr == "pending")
    neutral_count = func.count(outcome_expr).filter(outcome_expr == "neutral")
    total = func.count(ModelForecast.id)
    last_generated = func.max(ModelForecast.generated_at)
    first_generated = func.min(ModelForecast.generated_at)

    stmt = (
        select(
            ModelForecast.model_name,
            total.label("n"),
            hit_count.label("hits"),
            miss_count.label("misses"),
            indet_count.label("indeterminate"),
            pending_count.label("pending"),
            neutral_count.label("neutral"),
            last_generated.label("last_generated"),
            first_generated.label("first_generated"),
        )
        .where(
            ModelForecast.instrument_id == instrument.id,
            ModelForecast.horizon == horizon,
            ModelForecast.inputs_hash == BACKTEST_SOURCE_MARKER,
        )
        .group_by(ModelForecast.model_name)
        .order_by(ModelForecast.model_name)
    )
    result = await session.execute(stmt)
    models: list[dict[str, Any]] = []
    for row in result.all():
        scored = (row.hits or 0) + (row.misses or 0) + (row.indeterminate or 0)
        hit_rate = (row.hits / scored) if scored > 0 else 0.0
        models.append(
            {
                "name": row.model_name,
                "n": int(row.n or 0),
                "scored": int(scored),
                "hits": int(row.hits or 0),
                "misses": int(row.misses or 0),
                "indeterminate": int(row.indeterminate or 0),
                "pending": int(row.pending or 0),
                "neutral": int(row.neutral or 0),
                "hit_rate": round(hit_rate, 4),
                "last_generated_at": row.last_generated.isoformat()
                if row.last_generated is not None
                else None,
                "from_date": row.first_generated.date().isoformat()
                if row.first_generated is not None
                else None,
                "to_date": row.last_generated.date().isoformat()
                if row.last_generated is not None
                else None,
            }
        )

    return {"models": models, "horizon": horizon, "symbol": symbol}
