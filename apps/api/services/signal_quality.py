"""Signal Quality grading service (Phase 13 step 2).

Aggregates four already-existing signals into a single composite score 0-100
mapped to a letter grade (A+ / A / B / C / D). The grade is what the
dashboard chip displays; the four sub-scores are surfaced in a popover
so the analyst can see *why* a grade is what it is.

Sub-score weights are fixed (locked in docs/PHASE_13_PLAN.md). Calibration
of the weights themselves is out of scope — these are research-grade
heuristics for the demo, not a backtested decision rule.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.orm.adapter_runs import AdapterRun
from apps.api.models.orm.forecasts import ModelForecast

# ── Constants ────────────────────────────────────────────────────────────

_INPUT_DIVERSITY_SCORE: dict[str, int] = {"low": 10, "medium": 20, "high": 30}
_REGIME_STABILITY_SCORE: dict[str, int] = {
    "stable": 25,
    "mixed": 15,
    "volatile": 5,
}
_GRADE_CUTOFFS: list[tuple[int, str]] = [
    (90, "A+"),
    (80, "A"),
    (70, "B"),
    (60, "C"),
    (0, "D"),
]
# Adapters whose freshness gates "time_to_decision". The market adapter is
# excluded — it runs every 5 minutes by design and would always saturate the
# top bucket.
_FRESHNESS_ADAPTERS: frozenset[str] = frozenset(
    {"eia_storage", "cftc_cot", "nws_weather"}
)


@dataclass(frozen=True)
class SignalQualityResult:
    grade: str
    total_score: int
    sub_scores: dict[str, int]
    sub_score_max: dict[str, int]
    detail: dict[str, Any]


# ── Sub-score builders ────────────────────────────────────────────────────


def _score_input_diversity(ensemble_agreement: dict[str, Any]) -> int:
    diversity = str(ensemble_agreement.get("input_diversity", "low"))
    return _INPUT_DIVERSITY_SCORE.get(diversity, 0)


def _score_model_agreement(ensemble_agreement: dict[str, Any]) -> int:
    total = int(ensemble_agreement.get("total", 0))
    if total <= 0:
        return 0
    bullish = int(ensemble_agreement.get("bullish", 0))
    bearish = int(ensemble_agreement.get("bearish", 0))
    neutral = int(ensemble_agreement.get("neutral", 0))
    max_agreed = max(bullish, bearish, neutral)
    return int(round(25 * (max_agreed / total)))


def _classify_regime_stability(vol_regimes: list[str | None]) -> str:
    """Translate a list of vol_regime strings into stable/mixed/volatile."""
    distinct = {r for r in vol_regimes if r}
    if len(distinct) <= 1:
        return "stable"
    if len(distinct) == 2:
        return "mixed"
    return "volatile"


def _score_regime_stability(stability: str) -> int:
    return _REGIME_STABILITY_SCORE.get(stability, 0)


def _classify_time_to_decision(minutes_since: float | None) -> tuple[int, str]:
    """Convert minutes-since-latest-adapter-run into (score, bucket label)."""
    if minutes_since is None:
        return (0, "no-data")
    if minutes_since <= 60:
        return (20, "≤60m")
    if minutes_since <= 240:
        return (15, "≤4h")
    if minutes_since <= 1440:
        return (10, "≤24h")
    return (0, ">24h")


def _grade_for(score: int) -> str:
    for cutoff, grade in _GRADE_CUTOFFS:
        if score >= cutoff:
            return grade
    return "D"


# ── DB helpers ────────────────────────────────────────────────────────────


async def _vol_regimes_last_14d(
    session: AsyncSession, instrument_id: Any, now: datetime
) -> list[str | None]:
    """Distinct vol_regime values from forecasts in the last 14 days.

    Returns the raw list of values (not de-duped) so unit tests can verify
    the classifier's inputs.
    """
    from_dt = (now - timedelta(days=14)).replace(tzinfo=None)
    to_dt = now.replace(tzinfo=None)
    result = await session.execute(
        select(ModelForecast.vol_regime)
        .where(
            ModelForecast.instrument_id == instrument_id,
            ModelForecast.generated_at >= from_dt,
            ModelForecast.generated_at <= to_dt,
        )
    )
    return [row[0] for row in result.all()]


async def _minutes_since_latest_freshness_adapter(
    session: AsyncSession, now: datetime
) -> float | None:
    """Minutes since the most recent finished_at among the freshness adapters.

    Returns None when none of EIA/COT/NWS have completed a run, which the
    classifier maps to 0 (worst bucket).
    """
    result = await session.execute(
        select(AdapterRun.finished_at)
        .where(
            AdapterRun.adapter_name.in_(_FRESHNESS_ADAPTERS),
            AdapterRun.finished_at.is_not(None),
        )
        .order_by(AdapterRun.finished_at.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    if latest is None:
        return None
    # AdapterRun.finished_at is TIMESTAMPTZ → strip to compare with naive now.
    latest_naive = latest.replace(tzinfo=None) if latest.tzinfo else latest
    delta = now.replace(tzinfo=None) - latest_naive
    return max(0.0, delta.total_seconds() / 60.0)


# ── Public entry point ────────────────────────────────────────────────────


async def compute_grade(
    session: AsyncSession,
    *,
    instrument_id: Any,
    ensemble: dict[str, Any],
    now: datetime | None = None,
) -> SignalQualityResult:
    """Compute the Signal Quality grade for an instrument.

    Args:
        session: live DB session — used to read forecasts + adapter_runs.
        instrument_id: UUID of the instrument.
        ensemble: dict from ensemble.compute_ensemble — must include the
            "agreement" sub-dict with bullish/bearish/neutral/total counts
            and the input_diversity string.
        now: optional override for "current time" — tests inject this.

    Returns:
        SignalQualityResult with the composite grade, total score, four
        sub-scores, their max values for UI percentage bars, and a `detail`
        dict for the popover ("3 distinct vol regimes", "ran 28 min ago").
    """
    now = now or datetime.utcnow()
    agreement = ensemble.get("agreement") or {}

    diversity_score = _score_input_diversity(agreement)
    agreement_score = _score_model_agreement(agreement)

    vol_regimes = await _vol_regimes_last_14d(session, instrument_id, now)
    stability = _classify_regime_stability(vol_regimes)
    stability_score = _score_regime_stability(stability)

    minutes_since = await _minutes_since_latest_freshness_adapter(session, now)
    (freshness_score, freshness_bucket) = _classify_time_to_decision(minutes_since)

    total = diversity_score + agreement_score + stability_score + freshness_score
    grade = _grade_for(total)

    sub_scores = {
        "input_diversity": diversity_score,
        "model_agreement": agreement_score,
        "regime_stability": stability_score,
        "time_to_decision": freshness_score,
    }
    sub_score_max = {
        "input_diversity": 30,
        "model_agreement": 25,
        "regime_stability": 25,
        "time_to_decision": 20,
    }
    detail = {
        "input_diversity": str(agreement.get("input_diversity", "low")),
        "model_agreement_total": int(agreement.get("total", 0)),
        "model_agreement_max": max(
            int(agreement.get("bullish", 0)),
            int(agreement.get("bearish", 0)),
            int(agreement.get("neutral", 0)),
        ),
        "regime_stability": stability,
        "distinct_regimes_14d": len({r for r in vol_regimes if r}),
        "time_to_decision_bucket": freshness_bucket,
        "minutes_since_freshness_adapter": (
            int(round(minutes_since)) if minutes_since is not None else None
        ),
    }
    return SignalQualityResult(
        grade=grade,
        total_score=total,
        sub_scores=sub_scores,
        sub_score_max=sub_score_max,
        detail=detail,
    )
