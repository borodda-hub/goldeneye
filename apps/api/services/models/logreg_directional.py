"""Logistic-regression directional model — the platform's genuinely *trained*,
look-ahead-safe forecaster.

Unlike the heuristic ``factor_composite`` (hand-set weights), this LEARNS its
coefficients from data. On every call it builds price-derived features
(multi-horizon momentum, realized volatility, trend gap vs a moving average)
against the realized forward direction and fits a logistic regression by gradient
descent — using ONLY the closes it is handed. In the backtest that window is
strictly ``< as_of``, so the fit is walk-forward and **look-ahead-safe by
construction**: it never sees a bar from the future, and it passes the engine's
cheating-model proof unchanged. numpy only — no heavyweight ML dependency.

The fit is deterministic (zero init, fixed iterations), so the same window always
yields the same forecast. Feature coefficients give honest, inspectable
attributions; the in-sample fit accuracy is reported as a (clearly labelled)
caveat rather than dressed up as out-of-sample skill.
"""

from __future__ import annotations

import numpy as np

# Feature lookback, min training rows, and horizon → trading-day map.
_WARMUP = 20
_MIN_TRAIN_ROWS = 24
_HORIZON_TDAYS = {"1d": 1, "1w": 5, "1m": 21}
_ITERS = 400
_LR = 0.3
_FEATURE_NAMES = [
    "1-day momentum",
    "5-day momentum",
    "10-day momentum",
    "10-day volatility",
    "trend gap vs SMA-20",
]


def _features(c: np.ndarray, t: int) -> list[float]:
    """Features at index t, using only c[:t+1] (look-ahead-safe)."""
    rets = np.diff(c[t - 10 : t + 1]) / c[t - 10 : t]
    sma20 = float(np.mean(c[t - 19 : t + 1]))
    return [
        c[t] / c[t - 1] - 1.0,
        c[t] / c[t - 5] - 1.0,
        c[t] / c[t - 10] - 1.0,
        float(np.std(rets)) if rets.size else 0.0,
        (c[t] / sma20 - 1.0) if sma20 else 0.0,
    ]


def _sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30.0, 30.0)))


def _insufficient(horizon: str, need: int) -> "ForecastResult":  # noqa: F821
    from apps.api.services.models.moving_average_directional import ForecastResult

    return ForecastResult(
        model_name="logreg_directional",
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
                "factor": "Insufficient history to train",
                "weight": 1.0,
                "note": f"Need ~{need} closes to fit; returning neutral.",
            }
        ],
        inputs_used=["closes"],
    )


def predict(
    closes: list[float],
    horizon: str = "1d",
    latest_storage: dict | None = None,
    latest_cot: dict | None = None,
) -> "ForecastResult":  # noqa: F821
    from apps.api.services.models.moving_average_directional import ForecastResult

    h = _HORIZON_TDAYS.get(horizon, 1)
    c = np.asarray(closes, dtype=float)
    n = c.size
    need = _WARMUP + h + _MIN_TRAIN_ROWS
    if n < need or np.any(c <= 0):
        return _insufficient(horizon, need)

    # Walk-forward training set: features at t, realized direction at t+h.
    X = np.array([_features(c, t) for t in range(_WARMUP, n - h)])
    y = np.array([1.0 if c[t + h] > c[t] else 0.0 for t in range(_WARMUP, n - h)])

    # Standardize (guard zero-variance columns).
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd[sd == 0] = 1.0
    xs = (X - mu) / sd

    # Deterministic gradient-descent logistic regression.
    w = np.zeros(xs.shape[1])
    b = 0.0
    m = y.size
    for _ in range(_ITERS):
        p = _sigmoid(xs @ w + b)
        err = p - y
        w -= _LR * (xs.T @ err) / m
        b -= _LR * float(err.sum()) / m

    # Predict the latest bar (uses only past closes).
    x_last = (np.array(_features(c, n - 1)) - mu) / sd
    p_up = float(_sigmoid(np.array([x_last @ w + b]))[0])

    if p_up >= 0.55:
        direction = "bullish"
    elif p_up <= 0.45:
        direction = "bearish"
    else:
        direction = "neutral"
    edge = abs(p_up - 0.5)
    confidence = "high" if edge >= 0.15 else "medium" if edge >= 0.07 else "low"

    # Typical realized move over the horizon → expected_pct + range scale.
    avg_move = float(np.mean(np.abs(c[_WARMUP + h :] / c[_WARMUP:-h] - 1.0)))
    expected_pct = (p_up - 0.5) * 2.0 * avg_move
    in_sample_acc = float(np.mean((_sigmoid(xs @ w + b) >= 0.5) == (y >= 0.5)))

    # Feature attributions: signed contribution to the up-logit.
    contribs = w * x_last
    order = np.argsort(-np.abs(contribs))
    supporting: list[dict] = []
    contradicting: list[dict] = [
        {
            "factor": "Trained per-call on a rolling window",
            "weight": 0.5,
            "note": (
                f"In-sample fit accuracy {in_sample_acc:.0%} (not out-of-sample); "
                "coefficients re-estimate each call."
            ),
        }
    ]
    up = direction != "bearish"
    for idx in order[:3]:
        contrib = float(contribs[idx])
        pushes_up = contrib > 0
        item = {
            "factor": _FEATURE_NAMES[idx],
            "weight": round(min(abs(contrib), 1.0), 3),
            "note": f"{'raises' if pushes_up else 'lowers'} the modelled P(up).",
        }
        if (pushes_up and up) or (not pushes_up and not up):
            supporting.append(item)
        else:
            contradicting.append(item)
    if not supporting:
        supporting.append(
            {
                "factor": "Learned price-feature signal",
                "weight": round(edge, 3),
                "note": f"Modelled P(up) = {p_up:.0%}.",
            }
        )

    return ForecastResult(
        model_name="logreg_directional",
        horizon=horizon,
        direction=direction,
        confidence=confidence,
        expected_pct=round(expected_pct, 5),
        range_low_pct=round(expected_pct - avg_move, 5),
        range_high_pct=round(expected_pct + avg_move, 5),
        vol_regime=None,
        supporting=supporting,
        contradicting=contradicting,
        inputs_used=["closes"],
    )
