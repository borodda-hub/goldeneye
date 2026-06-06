"""Backtest engine — replay the model registry over historical NG price data.

Phase 10 step 1: in-memory replay loop. No HTTP, no DB writes, no UI. The
endpoint (step 3) and Signal Lab UI (step 4) will wrap this; look-ahead
safety + the cheating-model proof land in step 2.

Public surface:
    run_backtest(session, config) -> (rows, summary)

The replay walks day-by-day through the requested date range. For each
calendar date d:
  1. Build a ForecastContext snapshot strictly from data with ts/published_at
     < as_of_eod(d). The _context_as_of() helper is the single chokepoint
     for this — step 2 will lock it down with property-based tests; for
     now it just enforces the < bound on price closes.
  2. Run the requested model against that context.
  3. Look up the realized 1d close at d + horizon_days and compute
     (end/start) - 1 as realized_pct. Missing bars → outcome=pending.
  4. Score via the existing services.signal_scoring.score_forecast (same
     ±0.3% deadband as the Signal Lab history table).
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from statistics import pstdev
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.orm.cot import COTReport
from apps.api.models.orm.eia import EIAStorageReport
from apps.api.models.orm.prices import PriceBar
from apps.api.repos import contracts as contract_repo
from apps.api.repos import instruments as instr_repo
from apps.api.services.model_registry import ForecastContext
from apps.api.services.models.factor_composite import predict as factor_predict
from apps.api.services.models.logreg_directional import predict as logreg_predict
from apps.api.services.models.moving_average_directional import (
    ForecastResult,
)
from apps.api.services.models.moving_average_directional import (
    predict as ma_predict,
)
from apps.api.services.models.prophet_trend import predict as prophet_predict
from apps.api.services.models.volatility_regime import predict as vol_predict
from apps.api.services.signal_scoring import score_forecast

logger = logging.getLogger(__name__)

# Horizon → trading-day count. Matches the mapping in apps/api/routers/signals.py
# so the backtest's `outcome` field is comparable to the Signal Lab's live
# history table.
_HORIZON_DAYS: dict[str, int] = {"1d": 1, "1w": 7, "1m": 30}

# Minimum closes the model registry's run_all() requires. We mirror that
# rule here so the backtest produces "pending" / skip days rather than
# crashing on early dates.
_MIN_CLOSES = 55

# How far back of close history to feed the model per as_of.
# 100 is what live /v1/signals/current uses today.
_LOOKBACK_CLOSES = 100


# ── Public dataclasses ────────────────────────────────────────────────────


@dataclass(frozen=True)
class BacktestConfig:
    """Inputs to a backtest run."""

    model_name: str
    from_date: date
    to_date: date
    symbol: str = "NG"
    horizon: str = "1d"
    # Stateful models (currently only prophet_trend) can opt into periodic
    # retraining. None = stateless / reuse-fit. Not honored in step 1; placeholder
    # for the proper plumbing in a later phase.
    retrain_cadence_days: int | None = None


@dataclass(frozen=True)
class BacktestRow:
    """One forecast row from the replay loop."""

    generated_at: datetime
    model_name: str
    horizon: str
    direction: str
    confidence: str
    expected_pct: float | None
    realized_pct: float | None
    outcome: str
    delta_from_expected_pct: float | None
    vol_regime: str | None
    supporting: list[dict[str, Any]] = field(default_factory=list)
    contradicting: list[dict[str, Any]] = field(default_factory=list)
    inputs_used: list[str] = field(default_factory=lambda: ["closes"])


@dataclass(frozen=True)
class BacktestSummary:
    """Aggregate stats over a list of BacktestRow."""

    n: int
    scored: int
    hit_rate: float
    indeterminate_rate: float
    mean_delta: float
    std_delta: float


# ── Model dispatch ────────────────────────────────────────────────────────


# Per-model signatures differ, so wrap each in a uniform (model_name, ctx, horizon)
# adapter. Adding a model later means one new entry here plus a runtime check.
def _predict(model_name: str, ctx: ForecastContext, horizon: str) -> ForecastResult:
    if model_name == "moving_average_directional":
        return ma_predict(ctx.closes, horizon)
    if model_name == "volatility_regime":
        return vol_predict(ctx.closes, horizon)
    if model_name == "prophet_trend":
        return prophet_predict(ctx.closes, horizon)
    if model_name == "factor_composite":
        return factor_predict(
            ctx.closes,
            horizon,
            latest_storage=ctx.latest_storage,
            latest_cot=ctx.latest_cot,
        )
    if model_name == "logreg_directional":
        return logreg_predict(ctx.closes, horizon)
    raise ValueError(f"Unknown model_name: {model_name!r}")


SUPPORTED_MODELS: frozenset[str] = frozenset(
    {
        "moving_average_directional",
        "volatility_regime",
        "prophet_trend",
        "factor_composite",
        "logreg_directional",
    }
)


# ── Snapshot construction (step 1 chokepoint — step 2 hardens) ────────────


def _eod(d: date) -> datetime:
    """Naive UTC end-of-day for a calendar date. Matches PriceBar.ts being naive."""
    return datetime.combine(d, time(23, 59, 59, 999999))


def _start_of_day(d: date) -> datetime:
    return datetime.combine(d, time.min)


def _to_naive_utc(dt: datetime | None) -> datetime | None:
    """Normalize a datetime to naive UTC for cross-tz comparison.

    PriceBar.ts is TIMESTAMPTZ in the migration even though the ORM Mapped
    type doesn't say so; asyncpg returns tz-aware datetimes from those
    columns. The engine's internal as_of values are naive UTC, so the
    Python-side defensive checks need to normalize before comparing.
    """
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(UTC).replace(tzinfo=None)
    return dt


async def _closes_as_of(
    session: AsyncSession,
    contract_id: Any,
    as_of: datetime,
    n: int = _LOOKBACK_CLOSES,
) -> list[float]:
    """Return up to `n` daily closes with ts strictly less than `as_of`.

    The single chokepoint for "no future price data leaks into the context."
    `ts < as_of` is strict so a bar timestamped exactly at `as_of` is treated
    as future. EOD-of-day timestamps (23:59:59.999999) almost never match
    bar timestamps in practice, but strict-less-than keeps the invariant
    unambiguous regardless of clock skew.
    """
    result = await session.execute(
        select(PriceBar.ts, PriceBar.close)
        .where(
            PriceBar.contract_id == contract_id,
            PriceBar.resolution == "1d",
            PriceBar.ts < as_of,
        )
        .order_by(PriceBar.ts.desc())
        .limit(n)
    )
    rows = list(result.all())
    # Defensive: make double-sure no row leaked through with ts >= as_of.
    # Catches a future regression where someone relaxes the WHERE clause.
    # PriceBar.ts is TIMESTAMPTZ in the migration → asyncpg returns it
    # tz-aware; normalize both sides to naive UTC before comparing.
    as_of_naive = _to_naive_utc(as_of)
    for ts, _close in rows:
        ts_naive = _to_naive_utc(ts)
        if ts_naive is not None and ts_naive >= as_of_naive:
            raise RuntimeError(
                f"backtest look-ahead detected: bar ts={ts!r} >= as_of={as_of!r}"
            )
    closes = [float(close) for _ts, close in rows]
    return list(reversed(closes))


async def _storage_as_of(
    session: AsyncSession,
    as_of: datetime,
) -> dict[str, Any] | None:
    """Most-recent EIA storage report whose report_date is on or before
    as_of's calendar date. EIA releases Thursdays 10:30 ET — by EOD that
    Thursday the report IS public, so `report_date <= as_of.date()` is correct.

    Returns the dict shape factor_composite reads (delta_vs_consensus +
    actual_bcf), or None if no qualifying report exists.
    """
    as_of_date = as_of.date()
    result = await session.execute(
        select(EIAStorageReport)
        .where(EIAStorageReport.report_date <= as_of_date)
        .order_by(EIAStorageReport.report_date.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None
    if row.report_date is not None and row.report_date > as_of_date:
        raise RuntimeError(
            f"backtest look-ahead detected: EIA report_date={row.report_date!r} > as_of_date={as_of_date!r}"
        )
    return {
        "delta_vs_consensus": float(row.surprise_bcf)
        if row.surprise_bcf is not None
        else None,
        "actual_bcf": float(row.net_change_bcf)
        if row.net_change_bcf is not None
        else None,
    }


async def _cot_as_of(
    session: AsyncSession,
    as_of: datetime,
) -> dict[str, Any] | None:
    """Compute mm_net_delta = managed_money_net WoW change from the two
    most-recent COT reports whose release_date is on or before as_of's date.

    CFTC releases Fridays 15:30 ET — by EOD Friday the data is public, so
    `release_date <= as_of.date()` is correct.
    """
    as_of_date = as_of.date()
    result = await session.execute(
        select(COTReport)
        .where(COTReport.release_date <= as_of_date)
        .order_by(COTReport.release_date.desc())
        .limit(2)
    )
    rows = list(result.scalars().all())
    if len(rows) < 2:
        return None
    for r in rows:
        if r.release_date is not None and r.release_date > as_of_date:
            raise RuntimeError(
                f"backtest look-ahead detected: COT release_date={r.release_date!r} > as_of_date={as_of_date!r}"
            )
    curr_net = rows[0].managed_money_net
    prev_net = rows[1].managed_money_net
    if curr_net is None or prev_net is None:
        return None
    return {"mm_net_delta": float(curr_net - prev_net)}


async def _context_as_of(
    session: AsyncSession,
    symbol: str,
    contract_id: Any,
    as_of: datetime,
) -> ForecastContext:
    """Build a complete ForecastContext snapshot strictly from data known
    at `as_of`. The ONLY place in the engine that constructs a context;
    every leg goes through a chokepoint helper above.
    """
    closes = await _closes_as_of(session, contract_id, as_of)
    storage = await _storage_as_of(session, as_of)
    cot = await _cot_as_of(session, as_of)
    return ForecastContext(
        symbol=symbol,
        closes=closes,
        latest_storage=storage,
        latest_cot=cot,
    )


async def _close_on_or_after(
    session: AsyncSession,
    contract_id: Any,
    target_date: date,
    max_search_days: int = 5,
) -> float | None:
    """Return the daily close at the first bar with ts >= start-of-target_date.

    Search forward at most `max_search_days` so a horizon ending on a
    non-trading day (weekend) picks up Monday's close, but a horizon
    ending in the future returns None instead of grabbing a 6-month-later
    bar.
    """
    window_start = _start_of_day(target_date)
    window_end = _eod(target_date + timedelta(days=max_search_days))
    result = await session.execute(
        select(PriceBar.close)
        .where(
            PriceBar.contract_id == contract_id,
            PriceBar.resolution == "1d",
            PriceBar.ts >= window_start,
            PriceBar.ts <= window_end,
        )
        .order_by(PriceBar.ts)
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return float(row) if row is not None else None


async def _close_strictly_before(
    session: AsyncSession,
    contract_id: Any,
    as_of: datetime,
) -> float | None:
    """Return the most-recent daily close with ts < as_of. None if none exists."""
    result = await session.execute(
        select(PriceBar.close)
        .where(
            PriceBar.contract_id == contract_id,
            PriceBar.resolution == "1d",
            PriceBar.ts < as_of,
        )
        .order_by(PriceBar.ts.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return float(row) if row is not None else None


# ── Replay loop ───────────────────────────────────────────────────────────


def _build_row(
    *,
    generated_at: datetime,
    result: ForecastResult,
    realized_pct: float | None,
) -> BacktestRow:
    """Compose one BacktestRow by running score_forecast on the model output."""
    score = score_forecast(
        direction=result.direction,
        horizon=result.horizon,
        expected_pct=result.expected_pct,
        realized_pct=realized_pct,
    )
    return BacktestRow(
        generated_at=generated_at,
        model_name=result.model_name,
        horizon=result.horizon,
        direction=result.direction,
        confidence=result.confidence,
        expected_pct=result.expected_pct,
        realized_pct=score["realized_pct"],
        outcome=score["outcome"],
        delta_from_expected_pct=score["delta_from_expected_pct"],
        vol_regime=result.vol_regime,
        supporting=list(result.supporting or []),
        contradicting=list(result.contradicting or []),
        inputs_used=list(getattr(result, "inputs_used", ["closes"])),
    )


def _summarize(rows: list[BacktestRow]) -> BacktestSummary:
    n = len(rows)
    if n == 0:
        return BacktestSummary(0, 0, 0.0, 0.0, 0.0, 0.0)

    hits = sum(1 for r in rows if r.outcome == "hit")
    misses = sum(1 for r in rows if r.outcome == "miss")
    indet = sum(1 for r in rows if r.outcome == "indeterminate")
    scored = hits + misses + indet  # excludes pending + neutral

    hit_rate = hits / scored if scored > 0 else 0.0
    indeterminate_rate = indet / scored if scored > 0 else 0.0

    deltas = [r.delta_from_expected_pct for r in rows if r.delta_from_expected_pct is not None]
    mean_delta = sum(deltas) / len(deltas) if deltas else 0.0
    std_delta = pstdev(deltas) if len(deltas) > 1 else 0.0

    return BacktestSummary(
        n=n,
        scored=scored,
        hit_rate=round(hit_rate, 4),
        indeterminate_rate=round(indeterminate_rate, 4),
        mean_delta=round(mean_delta, 5),
        std_delta=round(std_delta, 5),
    )


async def _resolve_contract_id(session: AsyncSession, symbol: str) -> Any | None:
    """Pick a contract_id for the backtest to read closes against.

    Step 1 picks the current front-month and uses it for the whole window.
    That's a limitation: for dates predating that contract's listing, there
    won't be price bars and the loop will skip those days as `pending`.
    Multi-contract rollover handling is a Phase 11+ refinement (see plan
    §out-of-scope).
    """
    instrument = await instr_repo.get_by_symbol(session, symbol)
    if instrument is None:
        return None
    front = await contract_repo.get_front_month(session, instrument.id)
    return front.id if front is not None else None


async def run_backtest(
    session: AsyncSession,
    config: BacktestConfig,
    *,
    predict_fn: Callable[[str, ForecastContext, str], ForecastResult] | None = None,
) -> tuple[list[BacktestRow], BacktestSummary]:
    """Replay the configured model day-by-day. See module docstring.

    Args:
      session: open AsyncSession.
      config: BacktestConfig — model + symbol + date range + horizon.
      predict_fn: optional override for the model dispatcher. Tests inject
        a cheating model here (Step 2) to prove look-ahead is blocked.
    """
    if config.model_name not in SUPPORTED_MODELS:
        raise ValueError(
            f"Unknown model_name {config.model_name!r}; supported: {sorted(SUPPORTED_MODELS)}"
        )
    if config.horizon not in _HORIZON_DAYS:
        raise ValueError(
            f"Unsupported horizon {config.horizon!r}; supported: {sorted(_HORIZON_DAYS)}"
        )
    if config.from_date > config.to_date:
        return ([], _summarize([]))

    predict = predict_fn or _predict
    horizon_days = _HORIZON_DAYS[config.horizon]

    contract_id = await _resolve_contract_id(session, config.symbol)
    if contract_id is None:
        logger.warning("Backtest: no contract resolved for symbol=%r", config.symbol)
        return ([], _summarize([]))

    rows: list[BacktestRow] = []
    cur = config.from_date
    while cur <= config.to_date:
        as_of = _eod(cur)
        ctx = await _context_as_of(session, config.symbol, contract_id, as_of)
        if len(ctx.closes) < _MIN_CLOSES:
            cur += timedelta(days=1)
            continue

        result = predict(config.model_name, ctx, config.horizon)

        # Realized pct: (end / start) - 1, where start is the last close
        # strictly before as_of (the "anchor" the model saw) and end is the
        # first close on or after as_of + horizon_days.
        start_close = await _close_strictly_before(session, contract_id, as_of)
        end_date = cur + timedelta(days=horizon_days)
        end_close = await _close_on_or_after(session, contract_id, end_date)

        if start_close is not None and end_close is not None and start_close > 0:
            realized_pct: float | None = (end_close / start_close) - 1.0
        else:
            realized_pct = None

        rows.append(
            _build_row(
                generated_at=as_of,
                result=result,
                realized_pct=realized_pct,
            )
        )
        cur += timedelta(days=1)

    return (rows, _summarize(rows))


# Marker written to model_forecasts.inputs_hash so backtest-produced rows
# can be distinguished from the synthetic example_forecasts seed (which
# writes inputs_hash=None) and from any future live-persist flow.
BACKTEST_SOURCE_MARKER = "backtest:v1"


async def persist_backtest_rows(
    session: AsyncSession,
    *,
    instrument_id: Any,
    rows: list[BacktestRow],
    config: BacktestConfig,
) -> int:
    """Upsert rows into model_forecasts and remove the synthetic seed for
    this (instrument, model, horizon) window.

    Idempotency: there's no unique index on
    (instrument_id, model_name, horizon, generated_at), so we use a
    delete-then-insert in the date range covered by `rows`. Re-running the
    same backtest replaces — not duplicates — the previous output.

    Also deletes the synthetic example_forecasts seed (inputs_hash IS NULL)
    for the same (instrument, model, horizon) — keeps the Signal Lab
    history table reading a single coherent source per model.

    Returns the count of rows inserted.
    """
    if not rows:
        return 0

    from sqlalchemy import delete, insert

    from apps.api.models.orm.forecasts import ModelForecast

    ts_min = min(r.generated_at for r in rows)
    ts_max = max(r.generated_at for r in rows)

    # 1) Wipe any prior backtest rows in this window for the same model+horizon.
    await session.execute(
        delete(ModelForecast).where(
            ModelForecast.instrument_id == instrument_id,
            ModelForecast.model_name == config.model_name,
            ModelForecast.horizon == config.horizon,
            ModelForecast.generated_at >= ts_min,
            ModelForecast.generated_at <= ts_max,
        )
    )

    # 2) Also clear stale synthetic-seed rows for this model+horizon so the
    #    Signal Lab history table doesn't mix fake + real outcomes.
    await session.execute(
        delete(ModelForecast).where(
            ModelForecast.instrument_id == instrument_id,
            ModelForecast.model_name == config.model_name,
            ModelForecast.horizon == config.horizon,
            ModelForecast.inputs_hash.is_(None),
        )
    )

    # 3) Bulk-insert the fresh backtest rows. The `features` JSONB column
    #    carries the scored outcome so /v1/backtest/summary can compute
    #    aggregate hit-rate as a single SQL query — no re-scoring needed.
    payload = [
        {
            "generated_at": r.generated_at,
            "instrument_id": instrument_id,
            "model_name": r.model_name,
            "horizon": r.horizon,
            "direction": r.direction,
            "confidence": r.confidence,
            "expected_pct": r.expected_pct,
            "range_low_pct": None,
            "range_high_pct": None,
            "vol_regime": r.vol_regime,
            "supporting": r.supporting,
            "contradicting": r.contradicting,
            "features": {
                "realized_pct": r.realized_pct,
                "outcome": r.outcome,
                "delta_from_expected_pct": r.delta_from_expected_pct,
            },
            "inputs_hash": BACKTEST_SOURCE_MARKER,
            "caveats": None,
        }
        for r in rows
    ]
    await session.execute(insert(ModelForecast).values(payload))
    return len(payload)
