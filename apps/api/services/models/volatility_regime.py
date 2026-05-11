"""Volatility regime classifier."""
from __future__ import annotations


def classify(closes: list[float]) -> str:
    """
    Returns one of: compressed, normal, elevated, crisis
    Based on annualized realized vol of last 20 daily returns.
    < 0.25: compressed, < 0.45: normal, < 0.70: elevated, else crisis
    """
    from apps.api.services.models.moving_average_directional import (
        _annualized_vol,
        classify_vol_regime,
    )

    ann_vol = _annualized_vol(closes)
    return classify_vol_regime(ann_vol)


def predict(closes: list[float], horizon: str = "1d") -> "ForecastResult":  # noqa: F821
    """
    Returns ForecastResult with:
    - direction: if elevated/crisis and recent price up → bullish; if down → bearish; else neutral
    - confidence: low (vol regime is a condition, not a direction signal)
    - vol_regime: from classify()
    - supporting: current regime and transition probability
    - contradicting: regime classification uncertainty
    """
    from apps.api.services.models.moving_average_directional import ForecastResult

    regime = classify(closes)

    # Determine direction from recent price movement when in elevated/crisis regime
    direction: str = "neutral"
    if regime in ("elevated", "crisis") and len(closes) >= 2:
        if closes[-1] > closes[-2]:
            direction = "bullish"
        elif closes[-1] < closes[-2]:
            direction = "bearish"

    # Transition probability note (heuristic)
    transition_note = (
        f"Current regime: {regime}. Elevated/crisis regimes have a historical tendency "
        "to revert toward normal within 15-30 trading days, however persistence is common "
        "during structural supply/demand imbalances."
    )

    supporting = [
        {
            "factor": "Realized volatility regime",
            "weight": 0.6,
            "note": transition_note,
        },
    ]
    contradicting = [
        {
            "factor": "Regime classification uncertainty",
            "weight": 0.4,
            "note": (
                "Regime boundaries (0.25/0.45/0.70) are heuristic and may misclassify "
                "during structural market shifts. Regime alone does not determine direction."
            ),
        },
    ]

    return ForecastResult(
        model_name="volatility_regime",
        horizon=horizon,
        direction=direction,
        confidence="low",
        expected_pct=None,
        range_low_pct=None,
        range_high_pct=None,
        vol_regime=regime,
        supporting=supporting,
        contradicting=contradicting,
        inputs_used=["closes"],
    )
