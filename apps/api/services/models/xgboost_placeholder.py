"""
XGBoost placeholder — returns deterministic mock signal until real training pipeline ships.
Uses the last 20 closes to produce a mock directional signal based on momentum features.
"""
from __future__ import annotations


def predict(closes: list[float], horizon: str = "1d") -> "ForecastResult":  # noqa: F821
    """
    Return a deterministic mock directional forecast based on short-term momentum.

    Compares the mean of the last 5 closes to the mean of the prior 5 closes.
    If recent is higher, signal is bullish; otherwise bearish.

    Args:
        closes: List of daily close prices (most recent last).
        horizon: "1d" | "1w" | "1m"

    Returns:
        ForecastResult with confidence="low" and a clear placeholder note.
    """
    from apps.api.services.models.moving_average_directional import ForecastResult

    recent = closes[-5:] if len(closes) >= 5 else closes
    older = closes[-10:-5] if len(closes) >= 10 else closes[: len(closes) // 2]

    if not recent or not older:
        direction = "neutral"
    else:
        recent_mean = sum(recent) / len(recent)
        older_mean = sum(older) / len(older)
        direction = "bullish" if recent_mean > older_mean else "bearish"

    return ForecastResult(
        model_name="xgboost_placeholder",
        horizon=horizon,
        direction=direction,
        confidence="low",
        expected_pct=0.005 if direction == "bullish" else -0.005,
        range_low_pct=-0.02,
        range_high_pct=0.02,
        vol_regime=None,
        supporting=[
            {
                "factor": "Short-term price momentum",
                "weight": 0.5,
                "note": "Placeholder mock signal based on 5-day vs 10-day mean comparison.",
            }
        ],
        contradicting=[
            {
                "factor": "Model not trained on real data",
                "weight": 0.8,
                "note": "Placeholder until training pipeline ships.",
            }
        ],
    )
