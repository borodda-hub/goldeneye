"""Phase 26b — Holt linear-trend statistical model.

Verifies it tracks trend direction, is deterministic, degrades on thin history,
scales confidence to signal-to-noise, and reports honest projection caveats.
Engine-level look-ahead safety is covered by the cheating-model proof in
test_backtest_lookahead (holt_trend is added to SUPPORTED_MODELS there).
"""
from __future__ import annotations

import math

from apps.api.services.models.holt_trend import predict


def _trend(n: int, daily: float, start: float = 100.0, wiggle: float = 0.004) -> list[float]:
    """Deterministic trend with a small wiggle so residuals are non-zero."""
    return [start * (1 + daily) ** i * (1 + wiggle * math.sin(i)) for i in range(n)]


def test_uptrend_predicts_bullish():
    out = predict(_trend(60, 0.006), "1d")
    assert out.model_name == "holt_trend"
    assert out.direction == "bullish"
    assert out.expected_pct is not None and out.expected_pct > 0
    assert out.confidence in ("medium", "high")
    assert out.inputs_used == ["closes"]
    assert out.supporting


def test_downtrend_predicts_bearish():
    out = predict(_trend(60, -0.006), "1d")
    assert out.direction == "bearish"
    assert out.expected_pct is not None and out.expected_pct < 0


def test_flat_series_is_neutral_low():
    out = predict([100.0] * 60, "1d")
    assert out.direction == "neutral"
    assert out.confidence == "low"


def test_deterministic_same_window_same_forecast():
    closes = _trend(60, 0.004)
    a = predict(closes, "1d")
    b = predict(closes, "1d")
    assert (a.direction, a.confidence, a.expected_pct) == (
        b.direction,
        b.confidence,
        b.expected_pct,
    )


def test_longer_horizon_widens_range():
    closes = _trend(80, 0.005)
    d1 = predict(closes, "1d")
    w1 = predict(closes, "1w")
    span_1d = d1.range_high_pct - d1.range_low_pct
    span_1w = w1.range_high_pct - w1.range_low_pct
    assert span_1w > span_1d


def test_noisy_trend_lowers_confidence_vs_clean():
    clean = predict(_trend(80, 0.004, wiggle=0.002), "1d")
    noisy = predict(_trend(80, 0.004, wiggle=0.05), "1d")
    order = {"low": 0, "medium": 1, "high": 2}
    assert order[noisy.confidence] <= order[clean.confidence]


def test_insufficient_history_returns_neutral():
    out = predict(_trend(20, 0.005), "1d")
    assert out.direction == "neutral"
    assert out.confidence == "low"
    assert any("Insufficient" in c["factor"] for c in out.contradicting)


def test_rejects_nonpositive_closes():
    closes = _trend(60, 0.005)
    closes[30] = 0.0
    out = predict(closes, "1d")
    assert out.direction == "neutral"


def test_reports_projection_caveat():
    out = predict(_trend(60, 0.006), "1d")
    assert any("projection" in c["factor"].lower() for c in out.contradicting)
