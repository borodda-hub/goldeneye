"""Phase 8 — trained logistic-regression directional model.

Verifies it genuinely learns a directional pattern, is deterministic, degrades
on thin history, and reports look-ahead-safe metadata. Engine-level look-ahead
safety is covered by the existing cheating-model proof in test_backtest_lookahead.
"""
from __future__ import annotations

import math

from apps.api.services.models.logreg_directional import predict


def _trend(n: int, daily: float, start: float = 100.0) -> list[float]:
    """Deterministic trend with a small wiggle so features vary."""
    return [start * (1 + daily) ** i * (1 + 0.004 * math.sin(i)) for i in range(n)]


def test_learns_uptrend_predicts_bullish():
    out = predict(_trend(90, 0.006), "1d")
    assert out.model_name == "logreg_directional"
    assert out.direction == "bullish"
    assert out.confidence in ("medium", "high")
    assert out.expected_pct is not None and out.expected_pct > 0
    assert out.inputs_used == ["closes"]
    assert out.supporting  # non-empty attribution


def test_learns_downtrend_predicts_bearish():
    out = predict(_trend(90, -0.006), "1d")
    assert out.direction == "bearish"
    assert out.expected_pct is not None and out.expected_pct < 0


def test_deterministic_same_window_same_forecast():
    closes = _trend(90, 0.004)
    a = predict(closes, "1d")
    b = predict(closes, "1d")
    assert (a.direction, a.confidence, a.expected_pct) == (
        b.direction,
        b.confidence,
        b.expected_pct,
    )


def test_insufficient_history_returns_neutral():
    out = predict(_trend(30, 0.005), "1d")
    assert out.direction == "neutral"
    assert out.confidence == "low"
    assert any("Insufficient" in c["factor"] for c in out.contradicting)


def test_reports_in_sample_accuracy_caveat():
    out = predict(_trend(90, 0.006), "1d")
    # honesty: the per-call fit is flagged as in-sample, not out-of-sample skill.
    assert any("in-sample" in c["note"].lower() for c in out.contradicting)


def test_rejects_nonpositive_closes():
    closes = _trend(90, 0.005)
    closes[40] = 0.0
    out = predict(closes, "1d")
    assert out.direction == "neutral"  # guarded, no divide-by-zero blowup
