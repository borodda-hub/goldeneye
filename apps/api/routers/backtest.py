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
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db.session import get_db
from apps.api.repos import instruments as instr_repo
from apps.api.services.backtest import (
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
