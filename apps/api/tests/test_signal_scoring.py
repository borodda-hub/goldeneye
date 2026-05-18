import pytest

from apps.api.services.signal_scoring import score_forecast


def test_pending_when_realized_none():
    r = score_forecast("bullish", "1d", 0.01, None)
    assert r["outcome"] == "pending"
    assert r["realized_pct"] is None
    assert r["delta_from_expected_pct"] is None


def test_neutral_direction_returns_neutral():
    r = score_forecast("neutral", "1d", None, 0.02)
    assert r["outcome"] == "neutral"
    assert r["realized_pct"] == pytest.approx(0.02)


def test_boundary_exactly_deadband_is_indeterminate():
    r = score_forecast("bullish", "1d", 0.01, 0.003)
    assert r["outcome"] == "indeterminate"
    r2 = score_forecast("bearish", "1d", -0.01, -0.003)
    assert r2["outcome"] == "indeterminate"


def test_just_above_deadband_is_hit_or_miss():
    r = score_forecast("bullish", "1d", 0.01, 0.0031)
    assert r["outcome"] == "hit"
    r2 = score_forecast("bullish", "1d", 0.01, -0.0031)
    assert r2["outcome"] == "miss"


def test_bearish_hit():
    r = score_forecast("bearish", "1d", -0.01, -0.02)
    assert r["outcome"] == "hit"


def test_bearish_miss():
    r = score_forecast("bearish", "1d", -0.01, 0.01)
    assert r["outcome"] == "miss"


def test_nan_realized_treated_as_none():
    r = score_forecast("bullish", "1d", 0.01, float("nan"))
    assert r["outcome"] == "pending"


def test_inf_realized_treated_as_none():
    r = score_forecast("bullish", "1d", 0.01, float("inf"))
    assert r["outcome"] == "pending"


def test_delta_computed_when_both_present():
    r = score_forecast("bullish", "1d", 0.01, 0.016)
    assert r["delta_from_expected_pct"] == pytest.approx(0.006)


def test_delta_none_when_expected_missing():
    r = score_forecast("bullish", "1d", None, 0.016)
    assert r["delta_from_expected_pct"] is None


def test_zero_realized_is_indeterminate():
    r = score_forecast("bullish", "1d", 0.01, 0.0)
    assert r["outcome"] == "indeterminate"
