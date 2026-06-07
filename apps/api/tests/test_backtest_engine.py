"""Phase 10 Step 1 — backtest engine core tests.

Step 1 scope: the pure-Python logic in services/backtest.py without DB.
Look-ahead safety property tests + the cheating-model proof land in Step 2.
"""
from __future__ import annotations

from datetime import date, datetime

import pytest

from apps.api.services.backtest import (
    SUPPORTED_MODELS,
    BacktestConfig,
    BacktestRow,
    BacktestSummary,
    _build_row,
    _eod,
    _summarize,
    run_backtest,
)
from apps.api.services.models.moving_average_directional import ForecastResult

# ── Pure helpers ──────────────────────────────────────────────────────────


def test_eod_returns_naive_utc_end_of_day():
    eod = _eod(date(2026, 5, 12))
    assert eod.tzinfo is None
    assert eod.year == 2026 and eod.month == 5 and eod.day == 12
    assert (eod.hour, eod.minute, eod.second) == (23, 59, 59)


def test_supported_models_lists_all_four():
    assert SUPPORTED_MODELS == frozenset(
        {
            "moving_average_directional",
            "holt_trend",
            "factor_composite",
            "logreg_directional",
        }
    )


# ── _build_row ───────────────────────────────────────────────────────────


def _result(direction: str, expected_pct: float | None = 0.012) -> ForecastResult:
    return ForecastResult(
        model_name="moving_average_directional",
        horizon="1d",
        direction=direction,
        confidence="medium",
        expected_pct=expected_pct,
        range_low_pct=expected_pct - 0.02 if expected_pct is not None else None,
        range_high_pct=expected_pct + 0.02 if expected_pct is not None else None,
        vol_regime="normal",
        supporting=[{"factor": "test", "weight": 0.5, "note": ""}],
        contradicting=[{"factor": "counter", "weight": 0.3, "note": ""}],
        inputs_used=["closes"],
    )


def test_build_row_hit_on_matching_direction():
    row = _build_row(
        generated_at=datetime(2026, 5, 1),
        result=_result("bullish", expected_pct=0.01),
        realized_pct=0.018,
    )
    assert row.outcome == "hit"
    assert row.realized_pct == 0.018
    assert row.delta_from_expected_pct == pytest.approx(0.008)


def test_build_row_miss_on_opposite_direction():
    row = _build_row(
        generated_at=datetime(2026, 5, 1),
        result=_result("bullish"),
        realized_pct=-0.02,
    )
    assert row.outcome == "miss"


def test_build_row_indeterminate_inside_deadband():
    row = _build_row(
        generated_at=datetime(2026, 5, 1),
        result=_result("bullish"),
        realized_pct=0.002,
    )
    assert row.outcome == "indeterminate"


def test_build_row_pending_when_realized_missing():
    row = _build_row(
        generated_at=datetime(2026, 5, 1),
        result=_result("bullish"),
        realized_pct=None,
    )
    assert row.outcome == "pending"
    assert row.realized_pct is None
    assert row.delta_from_expected_pct is None


def test_build_row_neutral_direction_not_scored():
    row = _build_row(
        generated_at=datetime(2026, 5, 1),
        result=_result("neutral", expected_pct=0.0),
        realized_pct=0.02,
    )
    assert row.outcome == "neutral"


def test_build_row_preserves_supporting_and_inputs_used():
    row = _build_row(
        generated_at=datetime(2026, 5, 1),
        result=_result("bullish"),
        realized_pct=0.01,
    )
    assert row.supporting == [{"factor": "test", "weight": 0.5, "note": ""}]
    assert row.contradicting == [{"factor": "counter", "weight": 0.3, "note": ""}]
    assert row.inputs_used == ["closes"]


# ── _summarize ───────────────────────────────────────────────────────────


def _row(outcome: str, delta: float | None) -> BacktestRow:
    return BacktestRow(
        generated_at=datetime(2026, 5, 1),
        model_name="m",
        horizon="1d",
        direction="bullish",
        confidence="medium",
        expected_pct=0.01,
        realized_pct=0.01 + (delta or 0.0),
        outcome=outcome,
        delta_from_expected_pct=delta,
        vol_regime="normal",
    )


def test_summarize_empty_returns_zeros():
    summary = _summarize([])
    assert summary == BacktestSummary(0, 0, 0.0, 0.0, 0.0, 0.0)


def test_summarize_hit_rate_excludes_pending_and_neutral():
    rows = [
        _row("hit", 0.005),
        _row("hit", 0.003),
        _row("miss", -0.01),
        _row("indeterminate", 0.001),
        _row("pending", None),
        _row("pending", None),
        _row("neutral", None),
    ]
    summary = _summarize(rows)
    # Scored = 2 hits + 1 miss + 1 indeterminate = 4.
    assert summary.n == 7
    assert summary.scored == 4
    assert summary.hit_rate == pytest.approx(2 / 4)
    assert summary.indeterminate_rate == pytest.approx(1 / 4)


def test_summarize_mean_and_std_delta_skip_none():
    rows = [
        _row("hit", 0.01),
        _row("hit", 0.02),
        _row("miss", -0.01),
        _row("pending", None),  # excluded from mean
    ]
    summary = _summarize(rows)
    # mean of [0.01, 0.02, -0.01] = 0.00666...
    assert summary.mean_delta == pytest.approx(0.00667, abs=1e-4)
    assert summary.std_delta > 0


def test_summarize_zero_scored_rows_yields_zero_rates():
    rows = [_row("pending", None), _row("pending", None)]
    summary = _summarize(rows)
    assert summary.n == 2
    assert summary.scored == 0
    assert summary.hit_rate == 0.0
    assert summary.indeterminate_rate == 0.0


# ── run_backtest input validation (no DB needed) ──────────────────────────


@pytest.mark.asyncio
async def test_run_backtest_rejects_unknown_model():
    config = BacktestConfig(
        model_name="not_a_model",
        from_date=date(2026, 5, 1),
        to_date=date(2026, 5, 10),
    )
    with pytest.raises(ValueError, match="Unknown model_name"):
        await run_backtest(session=None, config=config)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_run_backtest_rejects_unsupported_horizon():
    config = BacktestConfig(
        model_name="moving_average_directional",
        from_date=date(2026, 5, 1),
        to_date=date(2026, 5, 10),
        horizon="42d",
    )
    with pytest.raises(ValueError, match="Unsupported horizon"):
        await run_backtest(session=None, config=config)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_run_backtest_reversed_dates_returns_empty():
    config = BacktestConfig(
        model_name="moving_average_directional",
        from_date=date(2026, 5, 10),
        to_date=date(2026, 5, 1),
    )
    rows, summary = await run_backtest(session=None, config=config)  # type: ignore[arg-type]
    assert rows == []
    assert summary.n == 0


# ── Dataclass invariants ──────────────────────────────────────────────────


def test_backtest_config_is_frozen():
    config = BacktestConfig(
        model_name="moving_average_directional",
        from_date=date(2026, 5, 1),
        to_date=date(2026, 5, 10),
    )
    with pytest.raises((AttributeError, TypeError)):
        config.model_name = "other"  # type: ignore[misc]


def test_backtest_row_is_frozen():
    row = _row("hit", 0.01)
    with pytest.raises((AttributeError, TypeError)):
        row.outcome = "miss"  # type: ignore[misc]


def test_backtest_summary_is_frozen():
    summary = _summarize([])
    with pytest.raises((AttributeError, TypeError)):
        summary.n = 5  # type: ignore[misc]
