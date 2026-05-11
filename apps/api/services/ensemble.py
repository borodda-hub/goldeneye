"""
Combines ForecastResult objects from multiple models into an ensemble signal.
"""
from __future__ import annotations

from apps.api.services.models.moving_average_directional import ForecastResult

CONFIDENCE_WEIGHTS: dict[str, int] = {"high": 3, "medium": 2, "low": 1}


def compute_ensemble(results: list[ForecastResult]) -> dict:  # type: ignore[type-arg]
    """
    Combine a list of ForecastResult objects into a weighted ensemble signal.

    Voting:
    - Each model contributes its CONFIDENCE_WEIGHT to its direction bucket.
    - Direction with highest total weight wins; ties resolve to "neutral".

    Ensemble confidence:
    - "high" if winning direction has >= 70% of total weight
    - "medium" if >= 50%
    - "low" otherwise

    vol_regime: taken from the volatility_regime model if present, else None.
    expected_pct: weighted average of non-None expected_pct values.
    range: weighted average of non-None range values.

    Returns:
        dict with keys: direction, confidence, vol_regime, expected_pct, range.
    """
    if not results:
        return {
            "direction": "neutral",
            "confidence": "low",
            "vol_regime": None,
            "expected_pct": None,
            "range": {"low_pct": -0.02, "high_pct": 0.02},
        }

    # Weighted vote
    vote_buckets: dict[str, float] = {"bullish": 0.0, "bearish": 0.0, "neutral": 0.0}
    total_weight = 0.0

    for result in results:
        w = float(CONFIDENCE_WEIGHTS.get(result.confidence, 1))
        direction = result.direction if result.direction in vote_buckets else "neutral"
        vote_buckets[direction] += w
        total_weight += w

    # Determine winning direction
    if total_weight == 0:
        winning_direction = "neutral"
        winning_weight = 0.0
    else:
        max_weight = max(vote_buckets.values())
        winners = [d for d, w in vote_buckets.items() if w == max_weight]
        if len(winners) > 1 or max_weight == 0:
            winning_direction = "neutral"
            winning_weight = vote_buckets["neutral"]
        else:
            winning_direction = winners[0]
            winning_weight = max_weight

    # Ensemble confidence from winning fraction
    if total_weight > 0:
        fraction = winning_weight / total_weight
    else:
        fraction = 0.0

    if fraction >= 0.70:
        ensemble_confidence = "high"
    elif fraction >= 0.50:
        ensemble_confidence = "medium"
    else:
        ensemble_confidence = "low"

    # vol_regime from volatility_regime model
    vol_regime: str | None = None
    for result in results:
        if result.model_name == "volatility_regime" and result.vol_regime is not None:
            vol_regime = result.vol_regime
            break
    # Fallback: any model that has vol_regime set
    if vol_regime is None:
        for result in results:
            if result.vol_regime is not None:
                vol_regime = result.vol_regime
                break

    # Weighted average expected_pct
    ep_sum = 0.0
    ep_weight = 0.0
    rl_sum = 0.0
    rh_sum = 0.0
    range_weight = 0.0

    for result in results:
        w = float(CONFIDENCE_WEIGHTS.get(result.confidence, 1))
        if result.expected_pct is not None:
            ep_sum += result.expected_pct * w
            ep_weight += w
        if result.range_low_pct is not None and result.range_high_pct is not None:
            rl_sum += result.range_low_pct * w
            rh_sum += result.range_high_pct * w
            range_weight += w

    expected_pct: float | None = ep_sum / ep_weight if ep_weight > 0 else None
    range_low = rl_sum / range_weight if range_weight > 0 else -0.02
    range_high = rh_sum / range_weight if range_weight > 0 else 0.02

    return {
        "direction": winning_direction,
        "confidence": ensemble_confidence,
        "vol_regime": vol_regime,
        "expected_pct": expected_pct,
        "range": {"low_pct": range_low, "high_pct": range_high},
    }
