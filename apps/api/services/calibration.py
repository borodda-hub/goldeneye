"""Calibration analysis service (Phase 13 step 3).

Buckets historical journal entries by claimed conviction and reports how
those buckets actually resolved. Powers the /calibration page's reliability
diagram and the auto-generated summary card.

Backwards-compat note: pre-Phase-13 journal entries don't have
`thesis_conviction_at_write`. The service falls back to the user-entered
`confidence_pct` field for those rows so the diagram has data from day one.

Sample-size guardrail: hit_rate is `None` when fewer than 3 resolved entries
fall in a bucket — the UI must render "n=N (need 3+)" rather than a
misleading percentage.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.orm.journal import UserDecisionJournal
from apps.api.repos import journal as journal_repo

MIN_RESOLVED_FOR_RATE: int = 3
SUMMARY_GAP_THRESHOLD_PCT: int = 5


@dataclass(frozen=True)
class CalibrationBucket:
    """One reliability-diagram bucket."""

    label: str  # e.g. "60-80"
    lower_pct: int  # inclusive
    upper_pct: int  # exclusive (except for the top bucket which is inclusive)
    claimed_mean: float | None  # mean conviction of entries in this bucket
    total_count: int
    resolved_count: int  # entries with resolved_direction in {hit, miss}
    hit_count: int
    hit_rate: float | None  # null when resolved_count < MIN_RESOLVED_FOR_RATE


@dataclass(frozen=True)
class CalibrationResult:
    instrument_code: str
    buckets: list[CalibrationBucket]
    total_entries: int
    resolved_entries: int
    unresolved_entries: int
    summary: str | None  # auto-generated copy, or None when no qualifying bucket


# ── Bucketing ─────────────────────────────────────────────────────────────


def _bucket_edges(bucket_count: int) -> list[tuple[int, int]]:
    """Return [(lower, upper), …] edges as integer percent boundaries.

    Equal-width buckets across [0, 100]. The last bucket includes 100 as
    its upper bound; all others are upper-exclusive.
    """
    if bucket_count <= 0:
        raise ValueError(f"bucket_count must be > 0, got {bucket_count}")
    if 100 % bucket_count != 0:
        raise ValueError(
            f"bucket_count must evenly divide 100, got {bucket_count}"
        )
    step = 100 // bucket_count
    return [(i * step, (i + 1) * step) for i in range(bucket_count)]


def _conviction_for(entry: UserDecisionJournal) -> int | None:
    """Effective conviction % for a journal entry.

    Prefers the Phase-13 thesis snapshot. Falls back to the user-entered
    confidence_pct for legacy rows. Returns None only when both are null,
    which shouldn't happen given confidence_pct is NOT NULL — but kept
    defensive in case of future schema relaxation.
    """
    if entry.thesis_conviction_at_write is not None:
        return entry.thesis_conviction_at_write
    return entry.confidence_pct


def _bucket_index_for(conviction: int, edges: list[tuple[int, int]]) -> int:
    """Find the bucket index for a conviction percentage.

    100 belongs to the last bucket. Out-of-range values are clamped
    rather than raising — calibration is a robustness story and we'd
    rather show a slightly-misbucketed row than 500.
    """
    if conviction <= 0:
        return 0
    if conviction >= 100:
        return len(edges) - 1
    for idx, (lo, hi) in enumerate(edges):
        if lo <= conviction < hi:
            return idx
    return len(edges) - 1


# ── Aggregation ───────────────────────────────────────────────────────────


def _build_bucket(
    edges: tuple[int, int],
    is_last: bool,
    entries: list[UserDecisionJournal],
) -> CalibrationBucket:
    lower, upper = edges
    label = f"{lower}-{upper}"
    if not entries:
        return CalibrationBucket(
            label=label,
            lower_pct=lower,
            upper_pct=upper,
            claimed_mean=None,
            total_count=0,
            resolved_count=0,
            hit_count=0,
            hit_rate=None,
        )

    convictions = [
        c for c in (_conviction_for(e) for e in entries) if c is not None
    ]
    claimed_mean = (
        sum(convictions) / len(convictions) if convictions else None
    )
    # Only "hit" / "miss" count toward the rate. "neutral" and "unresolved"
    # are excluded — neutral means the thesis didn't pay off in either
    # direction (no information), unresolved means we don't know yet.
    resolved = [
        e for e in entries if e.resolved_direction in ("hit", "miss")
    ]
    hits = sum(1 for e in resolved if e.resolved_direction == "hit")
    rate = (
        hits / len(resolved)
        if len(resolved) >= MIN_RESOLVED_FOR_RATE
        else None
    )
    return CalibrationBucket(
        label=label,
        lower_pct=lower,
        upper_pct=upper,
        claimed_mean=claimed_mean,
        total_count=len(entries),
        resolved_count=len(resolved),
        hit_count=hits,
        hit_rate=rate,
    )


def _summary_copy(buckets: list[CalibrationBucket]) -> str | None:
    """Pick the bucket with the largest claimed-vs-actual gap (≥ 5 pp).

    Returns deck-style copy or None when no bucket qualifies.
    """
    best: tuple[int, CalibrationBucket] | None = None
    for b in buckets:
        if b.hit_rate is None or b.claimed_mean is None:
            continue
        gap = abs(b.claimed_mean - b.hit_rate * 100)
        if gap < SUMMARY_GAP_THRESHOLD_PCT:
            continue
        gap_int = int(round(gap))
        if best is None or gap_int > best[0]:
            best = (gap_int, b)
    if best is None:
        return None
    _, b = best
    claimed = int(round(b.claimed_mean or 0))
    actual = int(round((b.hit_rate or 0) * 100))
    return f"Your {claimed}% theses resolved at {actual}% (n={b.resolved_count})."


# ── Public entry point ────────────────────────────────────────────────────


async def compute_calibration(
    session: AsyncSession,
    *,
    instrument_id: Any,
    instrument_code: str,
    bucket_count: int = 5,
) -> CalibrationResult:
    """Compute calibration buckets for an instrument's journal entries.

    Args:
        session: live DB session.
        instrument_id: UUID of the instrument.
        instrument_code: symbol string, echoed back in the response.
        bucket_count: number of equal-width conviction buckets. Must divide
            100 evenly. Default 5 → buckets at 0-20, 20-40, 40-60, 60-80, 80-100.

    Returns:
        CalibrationResult with one bucket per range, an overall summary
        sentence (or None), and counts of resolved + unresolved entries.
    """
    edges = _bucket_edges(bucket_count)
    entries = await journal_repo.list_with_resolutions(session, instrument_id)

    grouped: list[list[UserDecisionJournal]] = [[] for _ in edges]
    for entry in entries:
        conv = _conviction_for(entry)
        if conv is None:
            continue
        idx = _bucket_index_for(conv, edges)
        grouped[idx].append(entry)

    buckets = [
        _build_bucket(edge, idx == len(edges) - 1, group)
        for idx, (edge, group) in enumerate(zip(edges, grouped))
    ]
    resolved_total = sum(b.resolved_count for b in buckets)
    return CalibrationResult(
        instrument_code=instrument_code,
        buckets=buckets,
        total_entries=len(entries),
        resolved_entries=resolved_total,
        unresolved_entries=len(entries) - resolved_total,
        summary=_summary_copy(buckets),
    )
