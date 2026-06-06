"""Refresh persisted backtest rows for an instrument (default NG).

Purges any model_forecast rows for models no longer in SUPPORTED_MODELS (e.g.
the renamed-away xgboost_placeholder), then re-runs and persists the backtest for
every current model so the Signal Lab + Model Calibration Scorecard reflect the
real, honestly-named lineup over real prices.

Run with:  python -m apps.api.seeds.refresh_backtests [SYMBOL]
"""

from __future__ import annotations

import asyncio
import sys
from datetime import date
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_FROM = date(2025, 9, 1)
_TO = date(2026, 5, 15)


async def go(symbol: str) -> None:
    from sqlalchemy import delete, select

    from apps.api.db.session import get_session_factory
    from apps.api.models.orm.forecasts import ModelForecast
    from apps.api.models.orm.instruments import Instrument
    from apps.api.services.backtest import (
        SUPPORTED_MODELS,
        BacktestConfig,
        persist_backtest_rows,
        run_backtest,
    )

    async with get_session_factory()() as s:
        instr = (
            await s.execute(select(Instrument).where(Instrument.symbol == symbol))
        ).scalar_one_or_none()
        if instr is None:
            print(f"error: {symbol} not seeded")
            return

        purged = await s.execute(
            delete(ModelForecast).where(
                ModelForecast.instrument_id == instr.id,
                ModelForecast.model_name.notin_(tuple(SUPPORTED_MODELS)),
            )
        )
        await s.commit()
        print(f"purged {purged.rowcount or 0} stale-model forecast rows for {symbol}")

        for model in sorted(SUPPORTED_MODELS):
            cfg = BacktestConfig(
                model_name=model,
                from_date=_FROM,
                to_date=_TO,
                symbol=symbol,
                horizon="1d",
            )
            rows, summary = await run_backtest(s, cfg)
            n = await persist_backtest_rows(
                s, instrument_id=instr.id, rows=rows, config=cfg
            )
            await s.commit()
            print(f"  {model:30} persisted={n} hit_rate={summary.hit_rate:.3f}")
        print("backtest refresh complete.")


if __name__ == "__main__":
    sym = sys.argv[1].upper() if len(sys.argv) > 1 else "NG"
    asyncio.run(go(sym))
