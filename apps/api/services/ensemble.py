"""
Combines ForecastResult objects from multiple models into an ensemble signal.

Phase 26c — the ensemble is now *calibration-weighted*: each model's vote is scaled
by a weight derived from its measured historical Brier score (lower Brier = better
calibration = larger weight), not just by its self-reported confidence. The weight
mapping is ``model_weights_from_brier`` below; callers pass the resulting dict into
``compute_ensemble(..., model_weights=...)``. With no weights supplied the function
falls back to the pre-26c agreement-by-confidence behaviour (backward-compatible).

Honest scope (26c finding): this weighting is justified as **down-weighting
demonstrably-miscalibrated models** (e.g. the MA model's chronically overconfident
"high" calls). It does **not** claim to produce a calibrated ensemble *confidence
gradient* — the walk-forward harness in ``ensemble_calibration.py`` showed no reliable
gradient at any tested horizon (daily is near-random; the apparent 1w/1m gradients
were in-sample overfitting). Treat ensemble confidence as relative, not as a
realized-hit-rate promise.
"""
from __future__ import annotations

from typing import Literal

from apps.api.services.asset_config import DEFAULT as _ASSET_DEFAULT
from apps.api.services.asset_config import EnsembleBand
from apps.api.services.models.moving_average_directional import ForecastResult

CONFIDENCE_WEIGHTS: dict[str, int] = {"high": 3, "medium": 2, "low": 1}

_ALT_DATA_INPUTS = {"latest_storage", "latest_cot", "weather_anomaly"}
_NON_PRICE_INPUTS = {"vol_regime_signal"}  # signals derived from prices but not raw prices

# Calibration-weight bounds: no single model may count less than 0.4× or more than
# 2.0× the average, so a great score can't dominate and a poor one can't be silenced.
_WEIGHT_FLOOR = 0.4
_WEIGHT_CAP = 2.0
_BRIER_EPS = 1e-3

# ---------------------------------------------------------------------------
# LLM narrative-envelope confidence (Phase A2)
# ---------------------------------------------------------------------------
# The envelope confidence on the forecast-bearing LLM narratives (explain_signal,
# summarize_market, generate_thesis) is DERIVED, not hardcoded: it starts from the
# ensemble's agreement-derived confidence and is *down-modulated* by the predicted
# band width. A wider band ⇒ more uncertainty ⇒ it can only LOWER confidence, never
# raise it. The regime tie-rule is already baked into ``ensemble_confidence`` (see
# ``compute_ensemble``), so the regime is not a separate input here.
#
# Cutoffs are coarse heuristics on the ensemble's *fractional* band width
# (high_pct - low_pct). The envelope label is a 3-bucket relative signal, not a
# calibrated probability (consistent with the honest-scope note at the top of this
# module). Look-ahead-safe (S3): a pure function of values computed at request time.
EnvelopeConfidence = Literal["low", "medium", "high"]
_CONFIDENCE_RANK: dict[str, int] = {"low": 0, "medium": 1, "high": 2}
# Band-width cutoffs now live in the per-asset-class config (B5,
# asset_config.EnsembleBand). These module aliases are DERIVED from the commodity
# config (single source) and retained for the A2 test-lock + any direct importers.
_WIDE_BAND_PCT = _ASSET_DEFAULT.ensemble_band.wide          # commodity = 0.10
_VERY_WIDE_BAND_PCT = _ASSET_DEFAULT.ensemble_band.very_wide  # commodity = 0.18


def derive_envelope_confidence(
    *,
    ensemble_confidence: str,
    band_width: float | None,
    band_cfg: "EnsembleBand | None" = None,
) -> EnvelopeConfidence:
    """Derive an LLM-narrative envelope confidence from ensemble agreement + band width.

    ``ensemble_confidence`` already encodes the agreement (winning weighted fraction)
    and the regime tie-rule. ``band_width`` is the ensemble's fractional predicted
    range (``range["high_pct"] - range["low_pct"]``); a wide band can only lower the
    result. ``band_width=None`` returns the agreement tier unchanged. Never upgrades.

    ``band_cfg`` (B5) supplies the per-asset-class wide/very-wide cutoffs; defaults to
    the commodity (NG) set so existing callers stay byte-identical.
    """
    bc = band_cfg if band_cfg is not None else _ASSET_DEFAULT.ensemble_band
    base_rank = _CONFIDENCE_RANK.get(ensemble_confidence, 0)
    if band_width is not None:
        if band_width >= bc.very_wide:
            base_rank = _CONFIDENCE_RANK["low"]
        elif band_width >= bc.wide:
            base_rank = min(base_rank, _CONFIDENCE_RANK["medium"])
    if base_rank >= _CONFIDENCE_RANK["high"]:
        return "high"
    if base_rank == _CONFIDENCE_RANK["medium"]:
        return "medium"
    return "low"


def model_weights_from_brier(
    brier_by_model: dict[str, float | None],
) -> dict[str, float]:
    """Map measured per-model Brier scores to ensemble voting weights.

    Lower Brier (better calibration) → higher weight. Uses inverse-Brier normalised
    to mean 1.0 across the models that have a score, then clamps each to
    ``[_WEIGHT_FLOOR, _WEIGHT_CAP]``. Models with no score (None) get a neutral 1.0.
    Inverse-Brier is a standard, untuned mapping — no thresholds fit to a target.

    Returns a {model_name: weight} dict; an all-None / empty input yields all-1.0.
    """
    scored = {k: v for k, v in brier_by_model.items() if v is not None}
    if not scored:
        return {k: 1.0 for k in brier_by_model}
    inv = {k: 1.0 / max(v, _BRIER_EPS) for k, v in scored.items()}
    mean_inv = sum(inv.values()) / len(inv)
    weights: dict[str, float] = {}
    for name in brier_by_model:
        if name in inv and mean_inv > 0:
            w = inv[name] / mean_inv
            weights[name] = min(_WEIGHT_CAP, max(_WEIGHT_FLOOR, w))
        else:
            weights[name] = 1.0
    return weights


def _input_diversity(results: list[ForecastResult]) -> str:
    all_inputs: set[str] = set()
    for r in results:
        all_inputs.update(getattr(r, "inputs_used", ["closes"]))
    if all_inputs & _ALT_DATA_INPUTS:
        return "high"
    if all_inputs & _NON_PRICE_INPUTS:
        return "medium"
    return "low"


def compute_ensemble(
    results: list[ForecastResult],
    *,
    vol_regime: str | None = None,
    model_weights: dict[str, float] | None = None,
) -> dict:
    # Effective voting weight = self-reported confidence weight × the model's
    # calibration weight (Brier-derived). model_weights=None → all 1.0 (pre-26c).
    def _voter_weight(r: ForecastResult) -> float:
        cw = float(CONFIDENCE_WEIGHTS.get(r.confidence, 1))
        mw = (model_weights or {}).get(r.model_name, 1.0)
        return cw * mw

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

    # Weighted vote (confidence × calibration weight)
    vote_buckets: dict[str, float] = {"bullish": 0.0, "bearish": 0.0, "neutral": 0.0}
    total_weight = 0.0
    for result in results:
        w = _voter_weight(result)
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

    # vol_regime is shared CONTEXT, not a voter (Phase 26b): prefer the regime
    # passed in explicitly; otherwise read the regime stamped onto the results
    # by the registry. No model casts a directional vote on regime any more.
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
        w = _voter_weight(result)
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

    # Calibration weighting note (26c): surface that votes are accuracy-weighted,
    # and name the models pulled up/down so the weighting is transparent.
    if model_weights:
        up = sorted(
            (n for n, w in model_weights.items() if w > 1.05),
            key=lambda n: -model_weights[n],
        )
        down = sorted(
            (n for n, w in model_weights.items() if w < 0.95),
            key=lambda n: model_weights[n],
        )
        msg = "Votes weighted by measured calibration (Brier)"
        if up or down:
            parts = []
            if up:
                parts.append("up: " + ", ".join(up))
            if down:
                parts.append("down: " + ", ".join(down))
            msg += " — " + "; ".join(parts)
        rationale.append(msg + ".")

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
