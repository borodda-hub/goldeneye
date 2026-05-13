"""Seed historical model_forecasts so /signals' history table has scored content.

Without this, the Signal Lab's history panel renders "No scored forecasts in
range" on first load — the forecasts table is empty, the dashboard and
signals/current routes compute forecasts at request time but don't persist,
and there's no worker layer yet.

Strategy: generate 1d-horizon forecasts dated across the last 60 days, one
per day per model. Direction biased by the actual realized 1-day return in
the seeded price series, with noise — so the resulting hit-rate is roughly
55-65%, which is a realistic and visually interesting demo state (not all
hits, not coin-flip).

Idempotent: skip if ModelForecast rows already exist for any of our seeded
generated_at timestamps.
"""
from __future__ import annotations

import hashlib
import random
import uuid
from datetime import datetime, time, timedelta
from typing import Any

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

# Same four models compute_ensemble polls. Keep names in sync with services/models/*.
_MODELS = [
    "moving_average_directional",
    "prophet_trend",
    "volatility_regime",
    "xgboost_placeholder",
]

# Days of history to seed (each generated_at = noon UTC that day).
_HISTORY_DAYS = 60

# Per-model bias: probability of picking the "correct" direction given the
# realized return sign. Higher = better backtested hit-rate. Tuned to land
# the overall hit rate in the 55-65% band without making it obvious that
# the data is synthetic.
_MODEL_ACCURACY: dict[str, float] = {
    "moving_average_directional": 0.62,
    "prophet_trend": 0.55,
    "volatility_regime": 0.50,  # this one is mostly regime-only; 50% on direction
    "xgboost_placeholder": 0.60,
}

# Confidence distribution per model — biased toward "medium" with a long tail.
_CONFIDENCE_WEIGHTS: list[tuple[str, int]] = [
    ("medium", 5),
    ("high", 3),
    ("low", 2),
]


def _seeded_rng(generated_at: datetime, model_name: str) -> random.Random:
    """Deterministic per (date, model) seed so re-runs are stable."""
    key = f"{generated_at.isoformat()}|{model_name}".encode()
    seed = int.from_bytes(hashlib.sha256(key).digest()[:8], "big")
    return random.Random(seed)


def _choose_confidence(rng: random.Random) -> str:
    total = sum(w for _, w in _CONFIDENCE_WEIGHTS)
    pick = rng.random() * total
    cum = 0.0
    for value, weight in _CONFIDENCE_WEIGHTS:
        cum += weight
        if pick <= cum:
            return value
    return _CONFIDENCE_WEIGHTS[-1][0]


def _build_forecast_row(
    *,
    instrument_id: uuid.UUID,
    generated_at: datetime,
    model_name: str,
    actual_direction: str | None,
) -> dict[str, Any]:
    """Build one ModelForecast row dict suitable for bulk insert."""
    rng = _seeded_rng(generated_at, model_name)
    accuracy = _MODEL_ACCURACY[model_name]

    # Pick a direction biased by actual_direction when known.
    if actual_direction is not None and rng.random() < accuracy:
        direction = actual_direction
    else:
        # Wrong-way pick or no realized data available.
        direction = rng.choice(["bullish", "bearish", "neutral"])

    confidence = _choose_confidence(rng)

    # Expected pct magnitude depends on confidence + a small random factor.
    base_mag = {"low": 0.005, "medium": 0.012, "high": 0.022}[confidence]
    noise = rng.uniform(0.85, 1.15)
    if direction == "bullish":
        expected_pct = base_mag * noise
    elif direction == "bearish":
        expected_pct = -base_mag * noise
    else:
        expected_pct = rng.uniform(-0.002, 0.002)

    range_half = base_mag * 1.8
    range_low_pct = expected_pct - range_half
    range_high_pct = expected_pct + range_half

    vol_choices = ["compressed", "normal", "elevated", "crisis"]
    vol_regime = rng.choices(vol_choices, weights=[2, 5, 2, 1])[0]

    supporting = [
        {
            "factor": _supporting_factor(model_name),
            "weight": round(rng.uniform(0.35, 0.75), 2),
            "note": "Generated as part of the demo seed; not a live signal.",
        }
    ]
    contradicting = [
        {
            "factor": _contradicting_factor(model_name),
            "weight": round(rng.uniform(0.15, 0.45), 2),
            "note": "Seeded counter-evidence for the history table.",
        }
    ]

    return {
        "id": uuid.uuid4(),
        "generated_at": generated_at,
        "instrument_id": instrument_id,
        "model_name": model_name,
        "horizon": "1d",
        "direction": direction,
        "confidence": confidence,
        "expected_pct": round(expected_pct, 5),
        "range_low_pct": round(range_low_pct, 5),
        "range_high_pct": round(range_high_pct, 5),
        "vol_regime": vol_regime,
        "supporting": supporting,
        "contradicting": contradicting,
        "features": {},
        "inputs_hash": None,
        "caveats": None,
    }


def _supporting_factor(model_name: str) -> str:
    return {
        "moving_average_directional": "Short-term SMA crossover",
        "prophet_trend": "Trend component magnitude",
        "volatility_regime": "Regime persistence",
        "xgboost_placeholder": "Storage delta vs consensus",
    }[model_name]


def _contradicting_factor(model_name: str) -> str:
    return {
        "moving_average_directional": "RSI overbought/oversold reading",
        "prophet_trend": "Seasonality cross-current",
        "volatility_regime": "Regime transition risk",
        "xgboost_placeholder": "Crowded COT positioning",
    }[model_name]


async def _closes_by_date(
    session: AsyncSession, instrument_id: uuid.UUID
) -> dict[datetime, float]:
    """Map noon-UTC date → 1d close for the instrument's bound contract."""
    from apps.api.db.base import Base

    meta = Base.metadata
    price_bars = meta.tables["price_bars"]
    contracts = meta.tables["contracts"]

    rows = await session.execute(
        select(price_bars.c.ts, price_bars.c.close)
        .join(contracts, price_bars.c.contract_id == contracts.c.id)
        .where(
            contracts.c.instrument_id == instrument_id,
            price_bars.c.resolution == "1d",
        )
    )
    out: dict[datetime, float] = {}
    for ts, close in rows.all():
        if isinstance(ts, datetime):
            key = datetime.combine(ts.date(), time(12, 0))
            out[key] = float(close)
    return out


async def _closes_from_live_market(
    front_contract_code: str, lookback_days: int = 90
) -> dict[datetime, float]:
    """Fallback: pull recent daily closes from the live market adapter.

    Used when the instrument has no rows in price_bars yet (e.g. CL — Yahoo
    bars are pulled on-demand by the chart endpoint, never persisted).
    """
    from apps.api.adapters.registry import get_market

    market = get_market()
    now = datetime.utcnow()
    bars = await market.get_bars(
        front_contract_code,
        "1d",
        now - timedelta(days=lookback_days),
        now,
    )
    out: dict[datetime, float] = {}
    for bar in bars:
        ts = bar.get("ts")
        close = bar.get("close")
        if ts is None or close is None:
            continue
        if isinstance(ts, datetime):
            key = datetime.combine(ts.date(), time(12, 0))
            out[key] = float(close)
    return out


def _direction_from_returns(
    closes: dict[datetime, float],
    generated_at: datetime,
    horizon_days: int = 1,
) -> str | None:
    """Realized direction over the horizon, or None if either price is missing."""
    start_key = datetime.combine(generated_at.date(), time(12, 0))
    end_key = datetime.combine(
        (generated_at + timedelta(days=horizon_days)).date(), time(12, 0)
    )
    start = closes.get(start_key)
    end = closes.get(end_key)
    if start is None or end is None or start == 0:
        return None
    ret = (end / start) - 1.0
    deadband = 0.003
    if abs(ret) < deadband:
        return "neutral"
    return "bullish" if ret > 0 else "bearish"


async def seed_forecasts(
    session: AsyncSession, symbol: str = "NG"
) -> int:
    """Insert ~_HISTORY_DAYS × 4 forecast rows for `symbol`. Returns count inserted.

    Phase 14: takes a symbol so CL can be seeded alongside NG. When the
    instrument has no price_bars (CL is live-only via Yahoo), falls back to
    pulling 90 days of closes from the configured market adapter.
    """
    from apps.api.db.base import Base

    meta = Base.metadata
    instruments_t = meta.tables["instruments"]
    contracts_t = meta.tables["contracts"]
    forecasts_t = meta.tables["model_forecasts"]

    inst_row = (
        await session.execute(
            select(instruments_t).where(instruments_t.c.symbol == symbol)
        )
    ).first()
    if inst_row is None:
        raise RuntimeError(
            f"seed_forecasts: {symbol!r} instrument not found — load fixtures first"
        )
    instrument_id = inst_row.id

    # Idempotency: bail if we've already seeded forecasts for this instrument.
    existing = await session.execute(
        select(forecasts_t.c.id)
        .where(forecasts_t.c.instrument_id == instrument_id)
        .limit(1)
    )
    if existing.first() is not None:
        return 0

    # Pre-load realized prices so each forecast can know the "right" answer.
    # Tries DB first; falls back to a live market-adapter fetch when no rows
    # are seeded (CL path — Yahoo bars are pulled on demand by the chart
    # endpoint and never written to price_bars).
    closes = await _closes_by_date(session, instrument_id)
    if not closes:
        front_row = (
            await session.execute(
                select(contracts_t.c.contract_code).where(
                    contracts_t.c.instrument_id == instrument_id,
                    contracts_t.c.is_front_month.is_(True),
                )
            )
        ).first()
        if front_row is not None:
            try:
                closes = await _closes_from_live_market(
                    front_row.contract_code, lookback_days=_HISTORY_DAYS + 30
                )
            except Exception:
                # Stay defensive — synthetic forecasts can still seed with
                # all-random directions if live market is unreachable.
                closes = {}

    today = datetime.utcnow()
    rows: list[dict[str, Any]] = []
    for day_offset in range(_HISTORY_DAYS, 0, -1):
        generated_at = (today - timedelta(days=day_offset)).replace(
            hour=12, minute=0, second=0, microsecond=0
        )
        actual = _direction_from_returns(closes, generated_at)
        for model_name in _MODELS:
            rows.append(
                _build_forecast_row(
                    instrument_id=instrument_id,
                    generated_at=generated_at,
                    model_name=model_name,
                    actual_direction=actual,
                )
            )

    if not rows:
        return 0
    await session.execute(insert(forecasts_t).values(rows))
    return len(rows)
