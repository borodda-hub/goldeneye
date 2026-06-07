"""Factor (learned) model — Phase 26b candidate to replace the hand-set
``factor_composite``.

NOTE (26b gate outcome): on the re-seeded NG backtest this learned model did NOT
beat ``factor_composite`` on out-of-sample Brier (0.278 vs 0.259, a ~1 standard-error
difference — statistically a tie, but it is mildly *overconfident*). Per the
pre-registered 26b gate ("…or we keep the honest baseline and say so"),
``factor_composite`` was retained in the prod voter slot. This model is kept on the
bench, fully tested, for 26c to revisit once the ensemble is calibration-weighted
(which would naturally down-weight an overconfident voter). It is NOT in
SUPPORTED_MODELS or ``run_all`` today. See docs/BUILD_ROADMAP.md §26b.

Where ``factor_composite`` blended storage / COT / momentum with weights that were
*entirely hand-set* ("every weight is hand-set, not learned"), this LEARNS the
weight of its price-momentum core by fitting a walk-forward logistic regression on
the closes it is handed — the same dependency-free, look-ahead-safe approach as
``logreg_directional``, but with a slower, factor-style feature set (5- and 20-day
momentum plus a 20-day trend slope) to stay distinct from the fast logreg.

Honesty about the alt-data: the model is handed only the *current* storage and COT
readings (no historical alt-data series is available at predict time), so their
coefficients cannot be learned per call. They enter as a small, **theory-signed,
bounded tilt** on top of the learned momentum probability — smaller-build/larger-draw
and managed-money-getting-longer push bullish — and that tilt is labelled as such,
not dressed up as learned skill. When alt-data is missing the model falls back
cleanly to the learned price-only signal.
"""

from __future__ import annotations

import numpy as np

_WARMUP = 20
_MIN_TRAIN_ROWS = 24
_HORIZON_TDAYS = {"1d": 1, "1w": 5, "1m": 21}
_ITERS = 400
_LR = 0.3
_FEATURE_NAMES = ["5-day momentum", "20-day momentum", "20-day trend slope"]
# Max logit nudge each alt-data signal may contribute (theory-signed, bounded).
_ALT_TILT = 0.35


def _features(c: np.ndarray, t: int) -> list[float]:
    """Factor-style features at index t, using only c[:t+1] (look-ahead-safe)."""
    window = c[t - 19 : t + 1]
    x = np.arange(window.size, dtype=float)
    # Least-squares slope of the 20-bar window, normalised by price level.
    slope = float(np.polyfit(x, window, 1)[0]) / c[t] if c[t] else 0.0
    return [
        c[t] / c[t - 5] - 1.0,
        c[t] / c[t - 20] - 1.0,
        slope,
    ]


def _sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30.0, 30.0)))


def _logit(p: float) -> float:
    p = min(max(p, 1e-6), 1.0 - 1e-6)
    return float(np.log(p / (1.0 - p)))


def _insufficient(horizon: str, need: int) -> "ForecastResult":  # noqa: F821
    from apps.api.services.models.moving_average_directional import ForecastResult

    return ForecastResult(
        model_name="factor_learned",
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


def _alt_tilt(
    latest_storage: dict | None,
    latest_cot: dict | None,
) -> tuple[float, list[dict], list[str]]:
    """Theory-signed, bounded logit adjustment from the current alt-data reading.

    Returns (logit_delta, supporting_items, extra_inputs_used). NOT learned —
    the sign is fixed by fundamentals and the magnitude is bounded by _ALT_TILT.
    """
    delta = 0.0
    supporting: list[dict] = []
    inputs: list[str] = []
    if latest_storage is not None and latest_storage.get("delta_vs_consensus") is not None:
        d = float(latest_storage["delta_vs_consensus"])
        if d != 0.0:
            # Smaller build / larger draw (d<0) → bullish (+). Saturate at ~25 Bcf.
            tilt = _ALT_TILT * float(np.tanh(-d / 25.0))
            delta += tilt
            supporting.append(
                {
                    "factor": "EIA storage delta vs consensus",
                    "weight": round(abs(tilt), 3),
                    "note": (
                        f"Storage delta {d:.1f} Bcf adds a theory-signed "
                        f"{'bullish' if tilt > 0 else 'bearish'} tilt (not learned)."
                    ),
                }
            )
            inputs.append("latest_storage")
    if latest_cot is not None and latest_cot.get("mm_net_delta") is not None:
        m = float(latest_cot["mm_net_delta"])
        if m != 0.0:
            # Managed money getting longer (m>0) → bullish (+). Saturate at ~20k.
            tilt = _ALT_TILT * float(np.tanh(m / 20000.0))
            delta += tilt
            supporting.append(
                {
                    "factor": "COT managed-money net delta",
                    "weight": round(abs(tilt), 3),
                    "note": (
                        f"Managed-money WoW change {m:+.0f} adds a theory-signed "
                        f"{'bullish' if tilt > 0 else 'bearish'} tilt (not learned)."
                    ),
                }
            )
            inputs.append("latest_cot")
    return delta, supporting, inputs


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

    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd[sd == 0] = 1.0
    xs = (X - mu) / sd

    w = np.zeros(xs.shape[1])
    b = 0.0
    m = y.size
    for _ in range(_ITERS):
        p = _sigmoid(xs @ w + b)
        err = p - y
        w -= _LR * (xs.T @ err) / m
        b -= _LR * float(err.sum()) / m

    # Learned momentum probability for the latest bar.
    x_last = (np.array(_features(c, n - 1)) - mu) / sd
    base_logit = float(x_last @ w + b)
    p_momentum = float(_sigmoid(np.array([base_logit]))[0])

    # Fold in the theory-signed alt-data tilt (or fall back to price-only).
    tilt, alt_supporting, alt_inputs = _alt_tilt(latest_storage, latest_cot)
    p_up = float(_sigmoid(np.array([base_logit + tilt]))[0])

    if p_up >= 0.55:
        direction = "bullish"
    elif p_up <= 0.45:
        direction = "bearish"
    else:
        direction = "neutral"
    edge = abs(p_up - 0.5)
    confidence = "high" if edge >= 0.15 else "medium" if edge >= 0.07 else "low"

    avg_move = float(np.mean(np.abs(c[_WARMUP + h :] / c[_WARMUP:-h] - 1.0)))
    expected_pct = (p_up - 0.5) * 2.0 * avg_move
    in_sample_acc = float(np.mean((_sigmoid(xs @ w + b) >= 0.5) == (y >= 0.5)))

    inputs_used = ["closes", *alt_inputs]
    contribs = w * x_last
    order = np.argsort(-np.abs(contribs))
    supporting: list[dict] = list(alt_supporting)
    up = direction != "bearish"
    contradicting: list[dict] = [
        {
            "factor": "Momentum weights learned; alt-data tilt is theory-signed",
            "weight": 0.5,
            "note": (
                f"In-sample fit accuracy {in_sample_acc:.0%} (not out-of-sample). "
                "Momentum coefficients are fit per call; storage/COT enter as a "
                "bounded, fixed-sign tilt because no alt-data history is available "
                "at predict time."
            ),
        }
    ]
    if not alt_inputs:
        contradicting.append(
            {
                "factor": "Missing alt-data",
                "weight": 0.4,
                "note": "Storage/COT unavailable; falling back to the learned price signal only.",
            }
        )
    for idx in order[:2]:
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
                "factor": "Learned factor signal",
                "weight": round(edge, 3),
                "note": f"Modelled P(up) = {p_up:.0%} (momentum {p_momentum:.0%} + alt tilt).",
            }
        )

    return ForecastResult(
        model_name="factor_learned",
        horizon=horizon,
        direction=direction,
        confidence=confidence,
        expected_pct=round(expected_pct, 5),
        range_low_pct=round(expected_pct - avg_move, 5),
        range_high_pct=round(expected_pct + avg_move, 5),
        vol_regime=None,
        supporting=supporting,
        contradicting=contradicting,
        inputs_used=inputs_used,
    )
