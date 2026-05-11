"""
Prophet-based trend forecast.
If prophet is not installed, returns a stub result with confidence=low and a note.
"""
from __future__ import annotations

from datetime import date, timedelta


def predict(closes: list[float], horizon: str = "1w") -> "ForecastResult":  # noqa: F821
    """
    Fit a Prophet model and forecast the trend direction.

    Args:
        closes: List of daily close prices (most recent last).
        horizon: "1w" (7 days ahead) or "1m" (30 days ahead).

    Returns:
        ForecastResult with direction based on trend slope, or a stub if Prophet is not installed.
    """
    from apps.api.services.models.moving_average_directional import ForecastResult

    try:
        from prophet import Prophet  # type: ignore[import-untyped]
        import pandas as pd  # type: ignore[import-untyped]
    except ImportError:
        return ForecastResult(
            model_name="prophet_trend",
            horizon=horizon,
            direction="neutral",
            confidence="low",
            expected_pct=None,
            range_low_pct=None,
            range_high_pct=None,
            vol_regime=None,
            supporting=[
                {
                    "factor": "Stub mode",
                    "weight": 0.0,
                    "note": "Prophet package unavailable; model returning neutral.",
                }
            ],
            contradicting=[
                {
                    "factor": "Prophet package not installed",
                    "weight": 1.0,
                    "note": "Install with: uv pip install prophet",
                }
            ],
            inputs_used=["closes"],
        )

    if len(closes) < 10:
        return ForecastResult(
            model_name="prophet_trend",
            horizon=horizon,
            direction="neutral",
            confidence="low",
            expected_pct=None,
            range_low_pct=None,
            range_high_pct=None,
            vol_regime=None,
            supporting=[],
            contradicting=[
                {
                    "factor": "Insufficient data",
                    "weight": 1.0,
                    "note": "Need at least 10 data points to fit Prophet.",
                }
            ],
            inputs_used=["closes"],
        )

    # Build a daily date series ending today
    today = date.today()
    start = today - timedelta(days=len(closes) - 1)
    dates = [start + timedelta(days=i) for i in range(len(closes))]

    df = pd.DataFrame({"ds": dates, "y": closes})

    # Suppress Prophet's verbose output
    import logging
    prophet_logger = logging.getLogger("prophet")
    prev_level = prophet_logger.level
    prophet_logger.setLevel(logging.WARNING)

    try:
        model = Prophet(daily_seasonality=False, weekly_seasonality=True, yearly_seasonality=False)
        model.fit(df)

        periods = 7 if horizon == "1w" else 30
        future = model.make_future_dataframe(periods=periods)
        forecast = model.predict(future)

        # Trend slope: compare last forecast value to last historical value
        last_hist_trend = float(forecast.loc[forecast["ds"] <= pd.Timestamp(today), "trend"].iloc[-1])
        last_future_trend = float(forecast["trend"].iloc[-1])

        if last_hist_trend == 0:
            direction = "neutral"
            expected_pct = 0.0
        else:
            expected_pct = (last_future_trend / last_hist_trend) - 1.0
            if expected_pct > 0.005:
                direction = "bullish"
            elif expected_pct < -0.005:
                direction = "bearish"
            else:
                direction = "neutral"

        # Confidence: medium if we have decent history, low otherwise
        confidence = "medium" if len(closes) >= 60 else "low"

        # Range from yhat uncertainty
        last_row = forecast.iloc[-1]
        yhat = float(last_row["yhat"])
        yhat_lower = float(last_row["yhat_lower"])
        yhat_upper = float(last_row["yhat_upper"])
        range_low = (yhat_lower / closes[-1] - 1.0) if closes[-1] != 0 else -0.03
        range_high = (yhat_upper / closes[-1] - 1.0) if closes[-1] != 0 else 0.03

    finally:
        prophet_logger.setLevel(prev_level)

    supporting = [
        {
            "factor": "Prophet trend component",
            "weight": 0.6,
            "note": (
                f"Fitted trend suggests {direction} direction over {horizon} horizon "
                f"(expected_pct={expected_pct:.4f})."
            ),
        }
    ]
    contradicting = [
        {
            "factor": "Prophet seasonality uncertainty",
            "weight": 0.4,
            "note": (
                "Prophet trend extrapolation is sensitive to recent changepoints; "
                "short history may overfit seasonal noise."
            ),
        }
    ]

    return ForecastResult(
        model_name="prophet_trend",
        horizon=horizon,
        direction=direction,
        confidence=confidence,
        expected_pct=expected_pct,
        range_low_pct=range_low,
        range_high_pct=range_high,
        vol_regime=None,
        supporting=supporting,
        contradicting=contradicting,
        inputs_used=["closes"],
    )
