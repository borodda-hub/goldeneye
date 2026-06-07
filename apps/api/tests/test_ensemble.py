from apps.api.services.ensemble import compute_ensemble, model_weights_from_brier
from apps.api.services.models.moving_average_directional import ForecastResult


def _make_result(direction="bullish", confidence="medium", model_name="test", inputs_used=None):
    return ForecastResult(
        model_name=model_name,
        horizon="1d",
        direction=direction,
        confidence=confidence,
        expected_pct=0.01,
        range_low_pct=-0.02,
        range_high_pct=0.02,
        vol_regime=None,
        supporting=[{"factor": "test", "weight": 0.5, "note": "test"}],
        contradicting=[{"factor": "test contra", "weight": 0.5, "note": "test"}],
        inputs_used=inputs_used or ["closes"],
    )


def test_agreement_counts_sum_to_total():
    results = [
        _make_result("bullish"),
        _make_result("bullish"),
        _make_result("bearish"),
        _make_result("neutral"),
    ]
    out = compute_ensemble(results)
    a = out["agreement"]
    assert a["bullish"] + a["bearish"] + a["neutral"] == a["total"]
    assert a["total"] == 4
    assert a["bullish"] == 2
    assert a["bearish"] == 1
    assert a["neutral"] == 1


def test_input_diversity_high_when_storage_used():
    results = [
        _make_result("bullish", inputs_used=["closes", "latest_storage"]),
        _make_result("neutral", inputs_used=["closes"]),
    ]
    out = compute_ensemble(results)
    assert out["agreement"]["input_diversity"] == "high"


def test_input_diversity_low_when_all_price_only():
    results = [_make_result("bullish"), _make_result("bearish")]
    out = compute_ensemble(results)
    assert out["agreement"]["input_diversity"] == "low"


def test_tie_resolves_to_neutral():
    results = [
        _make_result("bullish", "high"),
        _make_result("bearish", "high"),
    ]
    out = compute_ensemble(results)
    assert out["direction"] == "neutral"


def test_tie_never_inherits_model_direction():
    # All same confidence — complete tie
    results = [
        _make_result("bullish", "medium"),
        _make_result("bearish", "medium"),
    ]
    out = compute_ensemble(results)
    assert out["direction"] not in ("bullish", "bearish")


def test_tie_in_elevated_regime_drops_confidence_to_low():
    results = [
        ForecastResult(
            model_name="volatility_regime", horizon="1d", direction="bullish",
            confidence="high", expected_pct=0.01, range_low_pct=-0.02, range_high_pct=0.02,
            vol_regime="elevated",
            supporting=[{"factor": "f", "weight": 0.5, "note": "n"}],
            contradicting=[{"factor": "c", "weight": 0.5, "note": "n"}],
            inputs_used=["closes"],
        ),
        _make_result("bearish", "high"),
    ]
    out = compute_ensemble(results)
    assert out["direction"] == "neutral"
    assert out["confidence"] == "low"
    assert any("amplified" in c for c in out["caveats"])


def test_tie_in_normal_regime_adds_caveat():
    results = [
        _make_result("bullish", "medium"),
        _make_result("bearish", "medium"),
    ]
    out = compute_ensemble(results)
    assert out["direction"] == "neutral"
    assert len(out["caveats"]) > 0
    assert any("no clear directional" in c or "disagree" in c for c in out["caveats"])


def test_confidence_rationale_is_non_empty():
    results = [_make_result("bullish"), _make_result("bullish")]
    out = compute_ensemble(results)
    assert len(out["confidence_rationale"]) >= 1


def test_empty_results_returns_safe_default():
    out = compute_ensemble([])
    assert out["direction"] == "neutral"
    assert out["confidence"] == "low"


# ── Phase 26c — calibration weighting ───────────────────────────────────────


def test_model_weights_lower_brier_gets_higher_weight():
    w = model_weights_from_brier(
        {"good": 0.20, "ok": 0.25, "bad": 0.34}
    )
    assert w["good"] > w["ok"] > w["bad"]
    # Normalised to mean ~1.0 (before clamping these all sit in-range).
    assert abs(sum(w.values()) / len(w) - 1.0) < 0.15


def test_model_weights_clamped_to_bounds():
    # An extreme spread would push weights past the bounds without clamping.
    w = model_weights_from_brier({"great": 0.001, "awful": 0.95})
    assert 0.4 <= w["great"] <= 2.0
    assert 0.4 <= w["awful"] <= 2.0


def test_model_weights_missing_score_is_neutral():
    w = model_weights_from_brier({"a": 0.25, "b": None})
    assert w["b"] == 1.0


def test_model_weights_all_none_uniform():
    w = model_weights_from_brier({"a": None, "b": None})
    assert w == {"a": 1.0, "b": 1.0}


def test_calibration_weighting_can_flip_a_confidence_tie():
    # Two bearish 'low' votes vs one bullish 'high' vote: by confidence weight the
    # bullish high (3) ties the two bearish lows (1+1=2)→ bullish wins. But if the
    # bullish model is badly calibrated (down-weighted) and the bearish ones are
    # well-calibrated (up-weighted), the bearish side should take over.
    results = [
        _make_result("bullish", "high", model_name="bad"),
        _make_result("bearish", "low", model_name="good1"),
        _make_result("bearish", "low", model_name="good2"),
    ]
    plain = compute_ensemble(results)
    assert plain["direction"] == "bullish"

    weights = model_weights_from_brier(
        {"bad": 0.34, "good1": 0.20, "good2": 0.20}
    )
    weighted = compute_ensemble(results, model_weights=weights)
    assert weighted["direction"] == "bearish"


def test_calibration_weighting_adds_rationale_line():
    results = [_make_result("bullish", "high", model_name="m1")]
    out = compute_ensemble(results, model_weights={"m1": 1.5})
    assert any("calibration" in r.lower() for r in out["confidence_rationale"])
