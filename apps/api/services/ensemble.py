"""
Combines ForecastResult objects from multiple models into an ensemble signal.
"""
from __future__ import annotations

from apps.api.services.models.moving_average_directional import ForecastResult

CONFIDENCE_WEIGHTS: dict[str, int] = {"high": 3, "medium": 2, "low": 1}

_ALT_DATA_INPUTS = {"latest_storage", "latest_cot", "weather_anomaly"}
_NON_PRICE_INPUTS = {"vol_regime_signal"}  # signals derived from prices but not raw prices


def _input_diversity(results: list[ForecastResult]) -> str:
    all_inputs: set[str] = set()
    for r in results:
        all_inputs.update(getattr(r, "inputs_used", ["closes"]))
    if all_inputs & _ALT_DATA_INPUTS:
        return "high"
    if all_inputs & _NON_PRICE_INPUTS:
        return "medium"
    return "low"


def compute_ensemble(results: list[ForecastResult]) -> dict:
    if not results:
        return {
            "direction": "neutral",
            "confidence": "low",
            "vol_regime": None,
            "expected_pct": None,
            "range": {"low_pct": -0.02, "high_pct": 0.02},
            "agreement": {"bullish": 0, "bearish": 0, "neutral": 0, "total": 0, "input_diversity": "low"},
            "confidence_rationale": ["No model results available."],
            "caveats": ["No models produced output; defaulting to neutral."],
        }

    # Count agreement
    agree_counts: dict[str, int] = {"bullish": 0, "bearish": 0, "neutral": 0}
    for r in results:
        d = r.direction if r.direction in agree_counts else "neutral"
        agree_counts[d] += 1

    # Weighted vote
    vote_buckets: dict[str, float] = {"bullish": 0.0, "bearish": 0.0, "neutral": 0.0}
    total_weight = 0.0
    for result in results:
        w = float(CONFIDENCE_WEIGHTS.get(result.confidence, 1))
        direction = result.direction if result.direction in vote_buckets else "neutral"
        vote_buckets[direction] += w
        total_weight += w

    # Determine winning direction — tie-break: always neutral
    is_tie = False
    caveats: list[str] = []
    if total_weight == 0:
        winning_direction = "neutral"
        winning_weight = 0.0
        is_tie = True
    else:
        max_weight = max(vote_buckets.values())
        winners = [d for d, w in vote_buckets.items() if w == max_weight]
        if len(winners) > 1 or max_weight == 0:
            winning_direction = "neutral"
            winning_weight = vote_buckets["neutral"]
            is_tie = True
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
    if vol_regime is None:
        for result in results:
            if result.vol_regime is not None:
                vol_regime = result.vol_regime
                break

    # Tie-break caveat (locked rule 1)
    if is_tie:
        if vol_regime in ("elevated", "crisis"):
            ensemble_confidence = "low"
            caveats.append(
                "Models disagree in elevated volatility regime; uncertainty is amplified in both directions."
            )
        else:
            caveats.append("Models disagree at low volatility; no clear directional signal.")

    # Weighted average expected_pct and range
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

    # Input diversity
    diversity = _input_diversity(results)

    # confidence_rationale
    total_models = len(results)
    dominant_dir = max(agree_counts, key=lambda d: agree_counts[d])
    dominant_count = agree_counts[dominant_dir]
    rationale: list[str] = [
        f"{dominant_count} of {total_models} models agree on {dominant_dir} direction.",
    ]
    if diversity == "high":
        rationale.append("Mixed price + fundamental signals (high input diversity).")
    elif diversity == "medium":
        rationale.append("Includes volatility-regime derived signals (medium input diversity).")
    else:
        rationale.append("All models read price series only (low input diversity).")

    # Check if any model had alt-data missing
    all_contradicting_factors: list[str] = []
    for r in results:
        for c in r.contradicting:
            all_contradicting_factors.append(c.get("factor", ""))
    if any("Missing alt-data" in f for f in all_contradicting_factors):
        rationale.append("Alt-data unavailable for one or more models; weight on price-only signals.")
    if any("Insufficient" in f or "insufficient" in f for f in all_contradicting_factors):
        rationale.append("One or more models signaled insufficient price history.")

    return {
        "direction": winning_direction,
        "confidence": ensemble_confidence,
        "vol_regime": vol_regime,
        "expected_pct": expected_pct,
        "range": {"low_pct": range_low, "high_pct": range_high},
        "agreement": {
            "bullish": agree_counts["bullish"],
            "bearish": agree_counts["bearish"],
            "neutral": agree_counts["neutral"],
            "total": total_models,
            "input_diversity": diversity,
        },
        "confidence_rationale": rationale,
        "caveats": caveats,
    }
