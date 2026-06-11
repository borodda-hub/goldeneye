"""Desk Calibration Score — Phase 7 (Calibration Platform).

The compounding moat: scores each analyst on *decision quality*, not outcome
luck. Hit-rate alone is luck-contaminated; the Brier score on their stated
conviction measures whether their confidence is actually reliable — the skill
signal. Together they separate "right for the right reasons" from "lucky".

The skill-vs-luck *verdict* (B2) makes that separation a statistical test, not a
label: a Wilson 95% CI on the directional hit-rate against the 0.50 chance
baseline. A desk earns ``skill`` only when the CI lower bound clears chance;
otherwise ``luck`` (not distinguishable from a coin flip on this sample) — so the
test correctly refuses to call noise skill. The blind ``random`` desk lands on
``luck`` by construction; that is the honesty guard working, not a defect.

Per-analyst grouping is by the journal's `user_id` (populated once accounts are
live; NULL = the unattributed/demo desk). A significance guardrail withholds a
score until an analyst has enough resolved decisions, so a 2-for-2 streak never
tops the desk. Auto-resolution (Phase 3) is what fills these in automatically.

Asset-class-agnostic + identity-agnostic: nothing here is commodity- or
Clerk-specific — it reads resolved journal rows and groups by user_id.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.orm.journal import UserDecisionJournal

# An analyst needs at least this many resolved decisions before a score shows —
# below it, calibration is noise (a 3-for-3 run isn't skill).
MIN_RESOLVED_FOR_SCORE: int = 10

# --- Skill-vs-luck significance test (B2) — PRE-REGISTERED thresholds. ---
# These are locked here, deliberately, BEFORE looking at any analyst's result, and
# are kept regardless of where the sample analyst / blind desks land. The verdict
# is a Wilson 95% confidence interval on the *directional* hit-rate against the
# coin-flip baseline. A desk is only credited with skill when the conservative
# lower bound clears chance — so a hot streak, or noise, is never called skill.
SKILL_BASELINE: float = 0.50  # chance hit-rate for a binary up/down call
WILSON_Z: float = 1.96  # two-sided 95% normal quantile

Verdict = Literal["skill", "luck", "insufficient"]


def wilson_interval(hits: int, n: int, *, z: float = WILSON_Z) -> tuple[float, float]:
    """Wilson score 95% CI for a binomial proportion (hits/n).

    Correct near 0/1 and for small n (unlike the normal approximation). Pure
    function of (hits, n) — no look-ahead, no DB. Returns the full [0, 1] interval
    for n == 0 (no information).
    """
    if n <= 0:
        return (0.0, 1.0)
    p = hits / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, center - half), min(1.0, center + half))


def skill_verdict(
    hits: int, n: int, *, min_resolved: int = MIN_RESOLVED_FOR_SCORE
) -> Verdict:
    """Skill / luck / insufficient from the Wilson lower bound vs the chance baseline.

    - ``insufficient`` — below the n-gate (no CI claim made on a thin record).
    - ``skill`` — the 95% CI lower bound beats chance (distinguishable from a coin flip).
    - ``luck`` — otherwise (the interval straddles or sits below chance): a hit-rate
      we cannot statistically separate from a coin flip given this sample. NOT an
      accusation of guessing — the honest "no demonstrated directional edge" verdict.
    """
    if n < min_resolved:
        return "insufficient"
    low, _ = wilson_interval(hits, n)
    return "skill" if low > SKILL_BASELINE else "luck"


@dataclass(frozen=True)
class AnalystScore:
    user_id: str | None
    n: int  # resolved decisions (hit/miss)
    brier: float | None  # decision-quality score (lower = better-calibrated)
    hit_rate: float | None  # raw outcome (luck-contaminated)
    mean_conviction: float | None  # avg claimed conviction %
    calibration_gap: float | None  # mean_conviction - hit_rate% (+ = overconfident)
    qualifies: bool  # n >= MIN_RESOLVED_FOR_SCORE
    wilson_low: float | None  # 95% CI lower bound on directional hit-rate
    wilson_high: float | None  # 95% CI upper bound on directional hit-rate
    verdict: Verdict  # skill / luck / insufficient (vs SKILL_BASELINE)


async def compute_desk_calibration(
    session: AsyncSession, *, min_resolved: int = MIN_RESOLVED_FOR_SCORE
) -> dict[str, Any]:
    """Per-analyst calibration over all resolved journal decisions.

    Ranked: qualifying analysts first, best-calibrated (lowest Brier) on top.
    """
    rows = (
        await session.execute(
            select(
                UserDecisionJournal.user_id,
                UserDecisionJournal.thesis_conviction_at_write,
                UserDecisionJournal.confidence_pct,
                UserDecisionJournal.resolved_direction,
            ).where(UserDecisionJournal.resolved_direction.in_(("hit", "miss")))
        )
    ).all()

    by_user: dict[Any, list[tuple[int, str]]] = {}
    for uid, thesis_conv, confidence, resolved in rows:
        conviction = thesis_conv if thesis_conv is not None else confidence
        if conviction is None:
            continue
        by_user.setdefault(uid, []).append((int(conviction), resolved))

    analysts: list[AnalystScore] = []
    for uid, items in by_user.items():
        n = len(items)
        hits = sum(1 for _, r in items if r == "hit")
        hit_rate = hits / n
        mean_conv = sum(c for c, _ in items) / n
        # Brier over the analyst's own stated conviction as the probability.
        brier = (
            sum(
                ((c / 100.0) - (1.0 if r == "hit" else 0.0)) ** 2 for c, r in items
            )
            / n
        )
        qualifies = n >= min_resolved
        verdict = skill_verdict(hits, n, min_resolved=min_resolved)
        # CI is only surfaced once the record qualifies — below the gate it would
        # be too wide to mean anything, and the verdict is "insufficient" anyway.
        low, high = wilson_interval(hits, n) if qualifies else (None, None)
        analysts.append(
            AnalystScore(
                user_id=str(uid) if uid is not None else None,
                n=n,
                brier=round(brier, 4),
                hit_rate=round(hit_rate, 4),
                mean_conviction=round(mean_conv, 1),
                calibration_gap=round(mean_conv - hit_rate * 100, 1),
                qualifies=qualifies,
                wilson_low=round(low, 4) if low is not None else None,
                wilson_high=round(high, 4) if high is not None else None,
                verdict=verdict,
            )
        )

    # Qualifying analysts first; within each group, best-calibrated (low Brier).
    analysts.sort(
        key=lambda a: (not a.qualifies, a.brier if a.brier is not None else 1.0)
    )
    return {
        "analysts": [asdict(a) for a in analysts],
        "min_resolved": min_resolved,
        "baseline": SKILL_BASELINE,
    }
