"""Phase 26c — ensemble confidence-calibration harness (the honesty guard).

These tests lock the methodology that caught the 26c in-sample illusion: an apparent
confidence gradient must survive *walk-forward* evaluation (weights from resolved
priors only), not just in-sample (full-window weights). If a future change makes the
ensemble's confidence look calibrated in-sample, this harness must still expose
whether it holds out-of-sample.
"""
from __future__ import annotations

from datetime import date, timedelta

from apps.api.services.ensemble_calibration import (
    EnsembleSample,
    confidence_bucket_calibration,
    is_monotonic_calibrated,
)
from apps.api.services.models.moving_average_directional import ForecastResult


def _r(model: str, direction: str, confidence: str, expected: float) -> ForecastResult:
    return ForecastResult(
        model_name=model,
        horizon="1d",
        direction=direction,
        confidence=confidence,
        expected_pct=expected,
        range_low_pct=None,
        range_high_pct=None,
        vol_regime=None,
        supporting=[],
        contradicting=[],
        inputs_used=["closes"],
    )


def _overall(buckets: dict) -> float:
    h = sum(b["hits"] for b in buckets.values())
    n = sum(b["n"] for b in buckets.values())
    return h / n if n else 0.0


def _divergence_samples(n: int = 10) -> list[EnsembleSample]:
    """A 'bad' model (bullish/high) is always wrong; a 'good' model (bearish/medium)
    is always right; the market always falls. Full-window weights down-weight the bad
    model so the *in-sample* ensemble is bearish (right) on every day — looks perfect.
    Walk-forward, day 1 has no priors → neutral weights → the bad model's high
    confidence wins → bullish (wrong). The harness must expose that gap.
    """
    base = date(2026, 1, 1)
    out: list[EnsembleSample] = []
    for i in range(n):
        out.append(
            EnsembleSample(
                as_of=base + timedelta(days=i),
                results=[
                    _r("bad", "bullish", "high", 0.01),
                    _r("good", "bearish", "medium", -0.01),
                ],
                realized_pct=-0.02,  # clear down move → bearish hits, bullish misses
                model_outcomes={"bad": "miss", "good": "hit"},
            )
        )
    return out


def test_walk_forward_reveals_in_sample_optimism():
    samples = _divergence_samples()
    in_sample = confidence_bucket_calibration(
        samples, horizon="1d", horizon_days=1, walk_forward=False
    )
    walk_forward = confidence_bucket_calibration(
        samples, horizon="1d", horizon_days=1, walk_forward=True
    )
    # In-sample the ensemble is right every day; walk-forward it misses at least the
    # first (no priors → bad model not yet down-weighted). The whole point of 26c.
    assert _overall(in_sample) == 1.0
    assert _overall(walk_forward) < _overall(in_sample)


def test_all_hits_dataset_reports_full_hit_rate():
    base = date(2026, 1, 1)
    samples = [
        EnsembleSample(
            as_of=base + timedelta(days=i),
            results=[_r("a", "bearish", "high", -0.01), _r("b", "bearish", "high", -0.01)],
            realized_pct=-0.02,
            model_outcomes={"a": "hit", "b": "hit"},
        )
        for i in range(6)
    ]
    buckets = confidence_bucket_calibration(
        samples, horizon="1d", horizon_days=1, walk_forward=True
    )
    assert _overall(buckets) == 1.0


def test_empty_samples_returns_no_buckets():
    assert confidence_bucket_calibration([], horizon="1d", horizon_days=1) == {}


def test_is_monotonic_true_when_high_beats_medium_beats_low():
    buckets = {
        "high": {"hits": 7, "n": 10, "hit_rate": 0.7},
        "medium": {"hits": 5, "n": 10, "hit_rate": 0.5},
        "low": {"hits": 3, "n": 10, "hit_rate": 0.3},
    }
    assert is_monotonic_calibrated(buckets) is True


def test_is_monotonic_false_on_inversion():
    # The exact failure shape 26c found at 1w walk-forward: high < medium.
    buckets = {
        "high": {"hits": 5, "n": 10, "hit_rate": 0.5},
        "medium": {"hits": 7, "n": 10, "hit_rate": 0.7},
    }
    assert is_monotonic_calibrated(buckets) is False


def test_is_monotonic_ignores_empty_buckets():
    buckets = {
        "high": {"hits": 6, "n": 10, "hit_rate": 0.6},
        "medium": {"hits": 0, "n": 0, "hit_rate": None},
        "low": {"hits": 4, "n": 10, "hit_rate": 0.4},
    }
    assert is_monotonic_calibrated(buckets) is True
