"""Desk Calibration Score — Phase 7 (Calibration Platform).

The compounding moat: scores each analyst on *decision quality*, not outcome
luck. Hit-rate alone is luck-contaminated; the Brier score on their stated
conviction measures whether their confidence is actually reliable — the skill
signal. Together they separate "right for the right reasons" from "lucky".

Per-analyst grouping is by the journal's `user_id` (populated once accounts are
live; NULL = the unattributed/demo desk). A significance guardrail withholds a
score until an analyst has enough resolved decisions, so a 2-for-2 streak never
tops the desk. Auto-resolution (Phase 3) is what fills these in automatically.

Asset-class-agnostic + identity-agnostic: nothing here is commodity- or
Clerk-specific — it reads resolved journal rows and groups by user_id.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.orm.journal import UserDecisionJournal

# An analyst needs at least this many resolved decisions before a score shows —
# below it, calibration is noise (a 3-for-3 run isn't skill).
MIN_RESOLVED_FOR_SCORE: int = 10


@dataclass(frozen=True)
class AnalystScore:
    user_id: str | None
    n: int  # resolved decisions (hit/miss)
    brier: float | None  # decision-quality score (lower = better-calibrated)
    hit_rate: float | None  # raw outcome (luck-contaminated)
    mean_conviction: float | None  # avg claimed conviction %
    calibration_gap: float | None  # mean_conviction - hit_rate% (+ = overconfident)
    qualifies: bool  # n >= MIN_RESOLVED_FOR_SCORE


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
        analysts.append(
            AnalystScore(
                user_id=str(uid) if uid is not None else None,
                n=n,
                brier=round(brier, 4),
                hit_rate=round(hit_rate, 4),
                mean_conviction=round(mean_conv, 1),
                calibration_gap=round(mean_conv - hit_rate * 100, 1),
                qualifies=n >= min_resolved,
            )
        )

    # Qualifying analysts first; within each group, best-calibrated (low Brier).
    analysts.sort(
        key=lambda a: (not a.qualifies, a.brier if a.brier is not None else 1.0)
    )
    return {
        "analysts": [asdict(a) for a in analysts],
        "min_resolved": min_resolved,
    }
