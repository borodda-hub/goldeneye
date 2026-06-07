"""Phase 26b — learned factor model (benched candidate; see module docstring).

This model lost the 26b Brier gate to the hand-set factor_composite baseline and is
NOT wired into the prod lineup, but it is kept fully tested for 26c to revisit.
Verifies the learned momentum core tracks direction, the alt-data tilt is
theory-signed and labelled (not learned), alt-data is optional with a clean
price-only fallback, the model is deterministic, and it degrades on thin history.
The model is look-ahead-safe by construction (trains only on the closes it is handed),
mirroring logreg_directional's proven walk-forward design.
"""
from __future__ import annotations

import math

from apps.api.services.models.factor_learned import predict


def _trend(n: int, daily: float, start: float = 100.0) -> list[float]:
    return [start * (1 + daily) ** i * (1 + 0.004 * math.sin(i)) for i in range(n)]


def test_learns_uptrend_predicts_bullish():
    out = predict(_trend(90, 0.006), "1d")
    assert out.model_name == "factor_learned"
    assert out.direction == "bullish"
    assert out.expected_pct is not None and out.expected_pct > 0
    assert out.inputs_used == ["closes"]  # no alt-data passed
    assert out.supporting


def test_learns_downtrend_predicts_bearish():
    out = predict(_trend(90, -0.006), "1d")
    assert out.direction == "bearish"
    assert out.expected_pct is not None and out.expected_pct < 0


def test_deterministic_same_window():
    closes = _trend(90, 0.004)
    a = predict(closes, "1d")
    b = predict(closes, "1d")
    assert (a.direction, a.confidence, a.expected_pct) == (
        b.direction,
        b.confidence,
        b.expected_pct,
    )


def test_storage_records_input_and_theory_signed_label():
    out = predict(_trend(90, 0.001), "1d", latest_storage={"delta_vs_consensus": -20.0})
    assert "latest_storage" in out.inputs_used
    label = "EIA storage delta vs consensus"
    factors = [s["factor"] for s in out.supporting]
    assert label in factors
    storage_item = next(s for s in out.supporting if s["factor"] == label)
    assert "not learned" in storage_item["note"].lower()


def test_cot_records_input():
    out = predict(_trend(90, 0.001), "1d", latest_cot={"mm_net_delta": 8000.0})
    assert "latest_cot" in out.inputs_used


def test_bullish_storage_tilts_prob_up():
    """A bullish storage surprise should not push the call more bearish than the
    price-only baseline (theory-signed tilt is additive in the bullish direction)."""
    closes = _trend(90, 0.001)
    base = predict(closes, "1d")
    tilted = predict(closes, "1d", latest_storage={"delta_vs_consensus": -25.0})
    assert (tilted.expected_pct or 0.0) >= (base.expected_pct or 0.0) - 1e-9


def test_missing_alt_data_fallback_labelled():
    out = predict(_trend(90, 0.005), "1d")
    factors = [c["factor"] for c in out.contradicting]
    assert "Missing alt-data" in factors


def test_reports_in_sample_caveat():
    out = predict(_trend(90, 0.006), "1d")
    assert any("in-sample" in c["note"].lower() for c in out.contradicting)


def test_insufficient_history_returns_neutral():
    out = predict(_trend(30, 0.005), "1d")
    assert out.direction == "neutral"
    assert out.confidence == "low"
    assert any("Insufficient" in c["factor"] for c in out.contradicting)


def test_rejects_nonpositive_closes():
    closes = _trend(90, 0.005)
    closes[40] = 0.0
    out = predict(closes, "1d")
    assert out.direction == "neutral"
