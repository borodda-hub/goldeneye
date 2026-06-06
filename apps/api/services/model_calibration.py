"""Model Calibration Scorecard — Phase 5 (Calibration Platform).

Turns the persisted backtest rows into a *reliability* view of each forecasting
model: when a model says "high confidence", how often is its directional call
actually right? And a Brier score per model — the standard scalar for
probabilistic-forecast quality (lower = better-calibrated). Optionally split by
volatility regime, so you can see e.g. a model that's sharp in normal markets but
overconfident in a crisis.

Models emit `direction + {low|medium|high}`, not a probability, so we map each
confidence level to a claimed probability-of-being-correct (an explicit,
auditable prior — NOT learned). Reliability then measures the gap between that
claim and the realized hit-rate; Brier scores the same gap as one number.

Pure aggregation over `model_forecasts` rows tagged with the backtest marker —
no model loop, no price lookups, no re-scoring.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.orm.forecasts import ModelForecast
from apps.api.services.backtest import BACKTEST_SOURCE_MARKER

# Claimed P(directional call is correct) per stated confidence. Explicit prior,
# documented so the reliability gap is interpretable. Tunable per asset class.
CONFIDENCE_PROB: dict[str, float] = {"low": 0.55, "medium": 0.65, "high": 0.75}

_UNKNOWN_REGIME = "unknown"


def _brier(buckets: list[dict[str, Any]]) -> tuple[float | None, int]:
    """Brier = mean((p - o)^2) over hit/miss rows, summed across buckets.
    Each bucket contributes hits*(p-1)^2 + misses*(p-0)^2."""
    total_sq = 0.0
    total_n = 0
    for b in buckets:
        p = b["claimed_prob"]
        h, m = b["hits"], b["misses"]
        total_sq += h * (p - 1.0) ** 2 + m * (p - 0.0) ** 2
        total_n += h + m
    if total_n == 0:
        return None, 0
    return round(total_sq / total_n, 4), total_n


def _scorecard(buckets: list[dict[str, Any]]) -> dict[str, Any]:
    """Reliability buckets (claimed vs actual per confidence) + Brier + hit-rate."""
    ordered = [
        b
        for level in ("low", "medium", "high")
        for b in buckets
        if b["confidence"] == level
    ]
    out_buckets = []
    hits = misses = 0
    for b in ordered:
        n = b["hits"] + b["misses"]
        hits += b["hits"]
        misses += b["misses"]
        out_buckets.append(
            {
                "confidence": b["confidence"],
                "claimed_prob": b["claimed_prob"],
                "actual_rate": round(b["hits"] / n, 4) if n else None,
                "n": n,
            }
        )
    brier, total_n = _brier(buckets)
    scored = hits + misses
    return {
        "brier": brier,
        "hit_rate": round(hits / scored, 4) if scored else None,
        "n": total_n,
        "buckets": out_buckets,
    }


async def compute_model_calibration(
    session: AsyncSession,
    instrument_id: Any,
    horizon: str,
    *,
    by_regime: bool = False,
) -> dict[str, Any]:
    """Per-model reliability + Brier over persisted backtest rows."""
    outcome = ModelForecast.features["outcome"].astext
    stmt = (
        select(
            ModelForecast.model_name,
            ModelForecast.vol_regime,
            ModelForecast.confidence,
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
            ModelForecast.vol_regime,
            ModelForecast.confidence,
            outcome,
        )
    )
    rows = (await session.execute(stmt)).all()

    # model -> "overall"/regime -> confidence -> {hits, misses, claimed_prob}
    models: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
    for r in rows:
        conf = r.confidence if r.confidence in CONFIDENCE_PROB else "medium"
        regime = r.vol_regime or _UNKNOWN_REGIME
        groups = ["overall"] + ([regime] if by_regime else [])
        for g in groups:
            bucket = (
                models.setdefault(r.model_name, {})
                .setdefault(g, {})
                .setdefault(
                    conf,
                    {
                        "confidence": conf,
                        "claimed_prob": CONFIDENCE_PROB[conf],
                        "hits": 0,
                        "misses": 0,
                    },
                )
            )
            if r.outcome == "hit":
                bucket["hits"] += r.n
            else:
                bucket["misses"] += r.n

    out_models: list[dict[str, Any]] = []
    for name in sorted(models):
        groups = models[name]
        card = {"name": name, **_scorecard(list(groups["overall"].values()))}
        if by_regime:
            card["by_regime"] = {
                regime: _scorecard(list(buckets.values()))
                for regime, buckets in groups.items()
                if regime != "overall"
            }
        out_models.append(card)

    return {"models": out_models, "confidence_prob": CONFIDENCE_PROB}
