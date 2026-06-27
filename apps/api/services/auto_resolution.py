"""Auto-resolution engine — Phase 3 (Calibration Platform).

Resolves open structured decisions against real market data: for each decision
whose horizon has elapsed, measure the realized move from the anchor price and
score it with the *same* look-ahead-safe logic the backtest uses
(`signal_scoring.score_forecast`), then write the result into the decision's
`resolved_direction` so calibration reflects it automatically — turning the
skill-vs-luck loop from manual into automatic.

Only decisions with `resolved_direction IS NULL` are touched, so a manual mark is
never overwritten. The deadband is the analyst's own `threshold_pct`: a move that
doesn't clear it resolves `neutral` (indeterminate), mirroring the backtest.

Asset-class-agnostic: it reads prices through the same contract/price_bars path
as everything else — a new asset class needs no change here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.orm.journal import UserDecisionJournal
from apps.api.models.orm.prices import PriceBar
from apps.api.repos import contracts as contract_repo
from apps.api.repos import ledger as ledger_repo
from apps.api.services import ledger as ledger_svc
from apps.api.services.metrics import AUTO_RESOLUTIONS, LEDGER_EVENTS
from apps.api.services.signal_scoring import score_forecast

# score_forecast outcome → journal resolved_direction (CHECK: hit/miss/neutral).
_OUTCOME_MAP: dict[str, str | None] = {
    "hit": "hit",
    "miss": "miss",
    "indeterminate": "neutral",  # move didn't clear the analyst's threshold
    "neutral": "neutral",  # neutral prediction (range-bound)
    "pending": None,
}


@dataclass
class ResolveResult:
    resolved: int = 0
    still_pending: int = 0
    no_price: int = 0
    by_outcome: dict[str, int] = field(default_factory=dict)


def _to_naive_utc(dt: datetime) -> datetime:
    """Normalize to naive UTC — price_bars.ts is TIMESTAMP WITHOUT TIME ZONE, so
    all comparisons must be naive (mirrors services/backtest.py)."""
    if dt.tzinfo is not None:
        return dt.astimezone(UTC).replace(tzinfo=None)
    return dt


async def _realized_close(
    session: AsyncSession, instrument_id, target: datetime
) -> float | None:
    """First real daily close on/after `target` for the instrument's front
    month — the price the decision is measured against."""
    front = await contract_repo.get_front_month(session, instrument_id)
    if front is None:
        return None
    close = (
        await session.execute(
            select(PriceBar.close)
            .where(
                PriceBar.contract_id == front.id,
                PriceBar.resolution == "1d",
                PriceBar.ts >= target,
            )
            .order_by(PriceBar.ts.asc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return float(close) if close is not None else None


async def resolve_open_decisions(
    session: AsyncSession, *, now: datetime | None = None
) -> ResolveResult:
    """Resolve every open structured decision whose horizon has elapsed."""
    now_aware = now or datetime.now(UTC)
    if now_aware.tzinfo is None:
        now_aware = now_aware.replace(tzinfo=UTC)
    now_naive = _to_naive_utc(now_aware)  # for ts comparisons (naive column)
    result = ResolveResult()

    open_entries = (
        await session.execute(
            select(UserDecisionJournal).where(
                UserDecisionJournal.predicted_direction.is_not(None),
                UserDecisionJournal.resolved_direction.is_(None),
                UserDecisionJournal.anchor_price.is_not(None),
                UserDecisionJournal.horizon_days.is_not(None),
            )
        )
    ).scalars().all()

    for e in open_entries:
        target = _to_naive_utc(e.created_at) + timedelta(days=int(e.horizon_days or 0))
        if target > now_naive:
            result.still_pending += 1
            continue

        realized = await _realized_close(session, e.instrument_id, target)
        if realized is None:
            result.no_price += 1
            continue

        anchor = float(e.anchor_price or 0.0)
        if anchor <= 0:
            result.no_price += 1
            continue

        move = realized / anchor - 1.0
        deadband = float(e.threshold_pct or 0.0) / 100.0
        scored = score_forecast(
            str(e.predicted_direction), f"{e.horizon_days}d", None, move, deadband
        )
        resolved = _OUTCOME_MAP.get(scored["outcome"])
        if resolved is None:
            result.no_price += 1
            continue

        e.resolved_direction = resolved
        e.resolved_at = now_aware  # tz-aware for the timestamptz column
        e.auto_resolved = True
        result.resolved += 1
        result.by_outcome[resolved] = result.by_outcome.get(resolved, 0) + 1
        AUTO_RESOLUTIONS.labels(outcome=resolved).inc()

        # B4: append the immutable resolution event. This is a post-decision
        # side-effect — it observes the resolution the engine just made and does
        # NOT influence what was resolved (S3 look-ahead invariant untouched).
        await ledger_repo.append_event(
            session,
            decision_id=e.id,
            user_id=e.user_id,
            event_type="resolved",
            occurred_at=now_aware,
            payload=ledger_svc.build_resolved_payload(
                outcome=resolved,
                resolved_at=now_aware,
                auto_resolved=True,
                anchor_price=anchor,
                realized_close=realized,
                move_pct=move,
                deadband_pct=float(e.threshold_pct or 0.0),
            ),
        )
        LEDGER_EVENTS.labels(event_type="resolved").inc()

    await session.flush()
    return result
