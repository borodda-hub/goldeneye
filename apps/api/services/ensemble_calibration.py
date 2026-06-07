"""Ensemble confidence-calibration harness — Phase 26c honesty guard.

The deliverable here is the **guard**, not a score. It measures whether the
calibration-weighted ensemble's confidence buckets are actually calibrated
out-of-sample — do "high"-confidence calls hit more than "medium"? — and it does so
**walk-forward**: each date's per-model weights use only outcomes resolved strictly
before that date.

This is the check that caught the Phase-26c in-sample illusion: at the 1w/1m
horizons the *in-sample* gradient looked clean and monotonic, but walk-forward it
inverted (1w) or flattened to sub-coin-flip (1m). Keeping this as a tested function
means no future change can quietly reintroduce that illusion — any claim that the
ensemble's confidence is calibrated must survive ``walk_forward=True`` here.

`confidence_bucket_calibration` is pure (feed it reconstructed per-date samples);
`measure_ensemble_calibration` is the DB entrypoint that assembles samples from the
backtest engine and returns both the in-sample and walk-forward views side by side.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from apps.api.services.ensemble import compute_ensemble, model_weights_from_brier
from apps.api.services.model_calibration import CONFIDENCE_PROB
from apps.api.services.models.moving_average_directional import ForecastResult
from apps.api.services.signal_scoring import score_forecast

_BUCKET_ORDER = ("high", "medium", "low")


@dataclass
class EnsembleSample:
    """One date's inputs to the ensemble replay.

    `results` is one ForecastResult per model for this date; `model_outcomes` maps
    each model_name to the resolved label ("hit"/"miss"/"pending"/…) of THAT date's
    call (which only becomes known at `as_of` + horizon — handled by the lag below).
    """

    as_of: date
    results: list[ForecastResult]
    realized_pct: float | None
    model_outcomes: dict[str, str] = field(default_factory=dict)


def _brier_contrib(confidence: str, outcome: str) -> float:
    p = CONFIDENCE_PROB.get(confidence, 0.5)
    o = 1.0 if outcome == "hit" else 0.0
    return (p - o) ** 2


def _brier_from_tally(tally: dict[str, list[float]]) -> dict[str, float | None]:
    return {m: (t[0] / t[1] if t[1] else None) for m, t in tally.items()}


def confidence_bucket_calibration(
    samples: list[EnsembleSample],
    *,
    horizon: str,
    horizon_days: int,
    walk_forward: bool = True,
) -> dict[str, dict[str, Any]]:
    """Replay the ensemble over `samples`; return per-confidence-bucket hit rates.

    ``walk_forward=True`` (the honest, OOS view): a date's model weights are derived
    only from per-model outcomes that have *resolved* before that date (a date's
    outcome resolves `horizon_days` later). ``walk_forward=False`` uses full-window
    Brier (in-sample, optimistic) — kept solely for the explicit comparison.

    Returns ``{confidence: {hits, n, hit_rate}}`` over scored (hit/miss) days only.
    """
    ordered = sorted(samples, key=lambda s: s.as_of)
    model_names = sorted({r.model_name for s in ordered for r in s.results})

    full_weights: dict[str, float] = {}
    if not walk_forward:
        tally: dict[str, list[float]] = {m: [0.0, 0.0] for m in model_names}
        for s in ordered:
            for r in s.results:
                oc = s.model_outcomes.get(r.model_name, "")
                if oc in ("hit", "miss"):
                    tally[r.model_name][0] += _brier_contrib(r.confidence, oc)
                    tally[r.model_name][1] += 1
        full_weights = model_weights_from_brier(_brier_from_tally(tally))

    buckets: dict[str, list[int]] = {}
    roll: dict[str, list[float]] = {m: [0.0, 0.0] for m in model_names}
    pending: list[tuple[date, str, float]] = []

    for s in ordered:
        if walk_forward:
            keep: list[tuple[date, str, float]] = []
            for rdate, m, c in pending:
                if rdate <= s.as_of:
                    roll[m][0] += c
                    roll[m][1] += 1
                else:
                    keep.append((rdate, m, c))
            pending = keep
            weights = model_weights_from_brier(_brier_from_tally(roll))
        else:
            weights = full_weights

        ens = compute_ensemble(s.results, model_weights=weights)
        sc = score_forecast(
            direction=ens["direction"],
            horizon=horizon,
            expected_pct=ens["expected_pct"],
            realized_pct=s.realized_pct,
        )
        if sc["outcome"] in ("hit", "miss"):
            b = buckets.setdefault(ens["confidence"], [0, 0])
            b[0] += 1 if sc["outcome"] == "hit" else 0
            b[1] += 1

        if walk_forward:
            resolve = s.as_of + timedelta(days=horizon_days)
            for r in s.results:
                oc = s.model_outcomes.get(r.model_name, "")
                if oc in ("hit", "miss"):
                    pending.append((resolve, r.model_name, _brier_contrib(r.confidence, oc)))

    return {
        c: {"hits": h, "n": n, "hit_rate": (h / n if n else None)}
        for c, (h, n) in buckets.items()
    }


def is_monotonic_calibrated(buckets: dict[str, dict[str, Any]]) -> bool:
    """True iff hit_rate(high) ≥ hit_rate(medium) ≥ hit_rate(low) over n>0 buckets.

    The literal 26c gate: do higher-confidence ensemble calls hit at least as often?
    """
    rates = [
        buckets[c]["hit_rate"]
        for c in _BUCKET_ORDER
        if c in buckets and buckets[c]["n"] > 0 and buckets[c]["hit_rate"] is not None
    ]
    return all(rates[i] >= rates[i + 1] for i in range(len(rates) - 1))


async def measure_ensemble_calibration(
    session: Any,
    *,
    symbol: str,
    from_date: date,
    to_date: date,
    horizon: str,
) -> dict[str, Any]:
    """DB entrypoint: replay the live model lineup over the backtest window and
    return both the in-sample and walk-forward ensemble bucket calibrations.

    Reproduces the Phase-26c NG finding on demand. No persistence, no router — a
    reusable analysis the gate test and any future endpoint can call.
    """
    from apps.api.services.backtest import (
        _HORIZON_DAYS,
        SUPPORTED_MODELS,
        BacktestConfig,
        run_backtest,
    )

    by_date: dict[date, dict[str, Any]] = {}
    for model in sorted(SUPPORTED_MODELS):
        cfg = BacktestConfig(
            model_name=model,
            from_date=from_date,
            to_date=to_date,
            symbol=symbol,
            horizon=horizon,
        )
        rows, _ = await run_backtest(session, cfg)
        for r in rows:
            d = r.generated_at.date()
            entry = by_date.setdefault(d, {"results": [], "realized": None, "outcomes": {}})
            entry["results"].append(
                ForecastResult(
                    model_name=r.model_name,
                    horizon=r.horizon,
                    direction=r.direction,
                    confidence=r.confidence,
                    expected_pct=float(r.expected_pct) if r.expected_pct is not None else None,
                    range_low_pct=None,
                    range_high_pct=None,
                    vol_regime=r.vol_regime,
                    supporting=[],
                    contradicting=[],
                    inputs_used=["closes"],
                )
            )
            if r.realized_pct is not None:
                entry["realized"] = float(r.realized_pct)
            entry["outcomes"][r.model_name] = r.outcome

    samples = [
        EnsembleSample(
            as_of=d,
            results=e["results"],
            realized_pct=e["realized"],
            model_outcomes=e["outcomes"],
        )
        for d, e in by_date.items()
    ]
    hd = _HORIZON_DAYS[horizon]
    return {
        "horizon": horizon,
        "n_days": len(samples),
        "in_sample": confidence_bucket_calibration(
            samples, horizon=horizon, horizon_days=hd, walk_forward=False
        ),
        "walk_forward": confidence_bucket_calibration(
            samples, horizon=horizon, horizon_days=hd, walk_forward=True
        ),
    }
