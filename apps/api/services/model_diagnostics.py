"""Model Diagnostics — Phase 26a (Model Intelligence v2).

Where `services/model_calibration.py` answers "is each model calibrated?" (Brier +
reliability buckets), this answers **"how does each model fail?"** over the same
persisted backtest rows:

- **directional bias** — does the model lean bullish/bearish, and does it only
  "work" in one direction (asymmetric hit-rate)?
- **Brier (Murphy) decomposition** — splits Brier into *reliability* (calibration:
  claimed prob vs realized hit-rate, lower = better), *resolution* (sharpness: how
  much the model discriminates across its confidence levels, higher = better), and
  base-rate *uncertainty*. Identity: ``brier = reliability - resolution + uncertainty``.
- **regime-conditional accuracy** — hit-rate per volatility regime (where it breaks).
- **feature-importance drift** (logreg only) — has the set of dominant price
  features shifted across the backtest window?

All descriptive and **in-sample over the backtest window** — NOT a forward claim.
Pure aggregation; the helpers below are unit-tested directly.
"""

from __future__ import annotations

from typing import Any, NamedTuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.orm.forecasts import ModelForecast
from apps.api.services.backtest import BACKTEST_SOURCE_MARKER
from apps.api.services.model_calibration import CONFIDENCE_PROB

_UNKNOWN_REGIME = "unknown"
_LOGREG = "logreg_directional"


class DiagRow(NamedTuple):
    """One grouped (direction, confidence, regime, outcome) tally for a model."""

    direction: str
    confidence: str
    vol_regime: str | None
    outcome: str  # "hit" | "miss"
    n: int


# ── Pure aggregations ──────────────────────────────────────────────────────


def _directional_bias(rows: list[DiagRow]) -> dict[str, Any]:
    """Call skew + per-direction hit-rate. A large hit_rate_gap means the model
    is only accurate in one direction (a one-sided edge, not a balanced signal)."""
    bull = bear = bull_hits = bear_hits = 0
    for r in rows:
        if r.direction == "bullish":
            bull += r.n
            if r.outcome == "hit":
                bull_hits += r.n
        elif r.direction == "bearish":
            bear += r.n
            if r.outcome == "hit":
                bear_hits += r.n
    directional = bull + bear
    bull_hr = bull_hits / bull if bull else None
    bear_hr = bear_hits / bear if bear else None
    return {
        "bullish_calls": bull,
        "bearish_calls": bear,
        "call_skew": round(bull / directional, 4) if directional else None,
        "bullish_hit_rate": round(bull_hr, 4) if bull_hr is not None else None,
        "bearish_hit_rate": round(bear_hr, 4) if bear_hr is not None else None,
        "hit_rate_gap": (
            round(bull_hr - bear_hr, 4)
            if bull_hr is not None and bear_hr is not None
            else None
        ),
    }


def _brier_decomposition(rows: list[DiagRow]) -> dict[str, Any]:
    """Murphy decomposition over confidence buckets. ``brier = reliability
    - resolution + uncertainty`` (matches model_calibration's scalar Brier)."""
    buckets: dict[str, list[int]] = {}  # conf -> [hits, misses]
    for r in rows:
        conf = r.confidence if r.confidence in CONFIDENCE_PROB else "medium"
        b = buckets.setdefault(conf, [0, 0])
        b[0 if r.outcome == "hit" else 1] += r.n

    total = sum(h + m for h, m in buckets.values())
    if total == 0:
        return {
            "n": 0,
            "base_rate": None,
            "reliability": None,
            "resolution": None,
            "uncertainty": None,
            "brier": None,
        }

    total_hits = sum(h for h, _m in buckets.values())
    base = total_hits / total
    reliability = resolution = 0.0
    for conf, (h, m) in buckets.items():
        n_k = h + m
        if n_k == 0:
            continue
        o_k = h / n_k
        p_k = CONFIDENCE_PROB[conf]
        w = n_k / total
        reliability += w * (p_k - o_k) ** 2
        resolution += w * (o_k - base) ** 2
    uncertainty = base * (1.0 - base)
    return {
        "n": total,
        "base_rate": round(base, 4),
        "reliability": round(reliability, 4),
        "resolution": round(resolution, 4),
        "uncertainty": round(uncertainty, 4),
        "brier": round(reliability - resolution + uncertainty, 4),
    }


def _regime_accuracy(rows: list[DiagRow]) -> dict[str, dict[str, Any]]:
    """Hit-rate + n per volatility regime."""
    agg: dict[str, list[int]] = {}
    for r in rows:
        reg = r.vol_regime or _UNKNOWN_REGIME
        a = agg.setdefault(reg, [0, 0])
        a[0 if r.outcome == "hit" else 1] += r.n
    out: dict[str, dict[str, Any]] = {}
    for reg in sorted(agg):
        h, m = agg[reg]
        n = h + m
        out[reg] = {"hit_rate": round(h / n, 4) if n else None, "n": n}
    return out


def _shares(factors: list[str]) -> dict[str, float]:
    total = len(factors)
    if not total:
        return {}
    counts: dict[str, int] = {}
    for f in factors:
        counts[f] = counts.get(f, 0) + 1
    return {f: c / total for f, c in counts.items()}


def _feature_drift(early: list[str], late: list[str]) -> dict[str, Any]:
    """Compare dominant feature shares between the early and late halves of the
    backtest window. A large per-feature `delta` means the model's leading driver
    changed over the window (a drift proxy — descriptive, not a forward claim)."""
    e, l = _shares(early), _shares(late)
    keys = set(e) | set(l)
    shifts = sorted(
        (
            {
                "factor": k,
                "early_share": round(e.get(k, 0.0), 4),
                "late_share": round(l.get(k, 0.0), 4),
                "delta": round(l.get(k, 0.0) - e.get(k, 0.0), 4),
            }
            for k in keys
        ),
        key=lambda d: abs(d["delta"]),
        reverse=True,
    )

    def _top(shares: dict[str, float]) -> list[dict[str, Any]]:
        return [
            {"factor": f, "share": round(s, 4)}
            for f, s in sorted(shares.items(), key=lambda kv: kv[1], reverse=True)[:3]
        ]

    return {
        "n_early": len(early),
        "n_late": len(late),
        "early_top": _top(e),
        "late_top": _top(l),
        "shifts": shifts[:5],
    }


def _feature_drift_from_rows(frows: list[Any]) -> dict[str, Any] | None:
    """Split (generated_at, supporting) rows into early/late halves and extract
    the `factor` labels logreg attributed in each half."""
    if not frows:
        return None
    mid = len(frows) // 2

    def factors(rows: list[Any]) -> list[str]:
        out: list[str] = []
        for _ts, supporting in rows:
            for item in supporting or []:
                f = item.get("factor") if isinstance(item, dict) else None
                if f:
                    out.append(f)
        return out

    return _feature_drift(factors(frows[:mid]), factors(frows[mid:]))


# ── DB entrypoint ──────────────────────────────────────────────────────────


async def compute_model_diagnostics(
    session: AsyncSession,
    instrument_id: Any,
    horizon: str,
) -> dict[str, Any]:
    """Per-model failure diagnostics over persisted backtest rows."""
    outcome = ModelForecast.features["outcome"].astext
    stmt = (
        select(
            ModelForecast.model_name,
            ModelForecast.direction,
            ModelForecast.confidence,
            ModelForecast.vol_regime,
            outcome.label("outcome"),
            func.count(ModelForecast.id).label("n"),
        )
        .where(
            ModelForecast.instrument_id == instrument_id,
            ModelForecast.horizon == horizon,
            ModelForecast.inputs_hash == BACKTEST_SOURCE_MARKER,
            outcome.in_(("hit", "miss")),
        )
        .group_by(
            ModelForecast.model_name,
            ModelForecast.direction,
            ModelForecast.confidence,
            ModelForecast.vol_regime,
            outcome,
        )
    )
    rows = (await session.execute(stmt)).all()

    by_model: dict[str, list[DiagRow]] = {}
    for r in rows:
        by_model.setdefault(r.model_name, []).append(
            DiagRow(r.direction, r.confidence, r.vol_regime, r.outcome, r.n)
        )

    # Feature-drift inputs: logreg's per-row supporting attributions over time.
    fstmt = (
        select(ModelForecast.generated_at, ModelForecast.supporting)
        .where(
            ModelForecast.instrument_id == instrument_id,
            ModelForecast.horizon == horizon,
            ModelForecast.inputs_hash == BACKTEST_SOURCE_MARKER,
            ModelForecast.model_name == _LOGREG,
        )
        .order_by(ModelForecast.generated_at)
    )
    frows = (await session.execute(fstmt)).all()
    drift = _feature_drift_from_rows(frows)

    out_models: list[dict[str, Any]] = []
    for name in sorted(by_model):
        mr = by_model[name]
        card: dict[str, Any] = {
            "name": name,
            "directional_bias": _directional_bias(mr),
            "brier_decomposition": _brier_decomposition(mr),
            "regime_accuracy": _regime_accuracy(mr),
        }
        if name == _LOGREG:
            card["feature_drift"] = drift
        out_models.append(card)

    return {"models": out_models, "confidence_prob": CONFIDENCE_PROB}
