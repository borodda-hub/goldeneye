from apps.api.services.ensemble import compute_ensemble
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
