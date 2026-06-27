"""Phase B4 — decision/audit ledger repository.

APPEND + READ only. There is deliberately **no update or delete method** — the
ledger is append-only at the app layer, and the DB trigger enforces it even if a
caller tried (see migration 011). Scoping is by `user_id` (copied onto each event
at append time), so the ledger read isolates per user exactly like the journal.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.orm.ledger import DecisionLedgerEvent
from apps.api.services.ledger import canonical_hash


async def _latest_hash_for(
    session: AsyncSession, decision_id: uuid.UUID
) -> str | None:
    """The most recent event's `row_hash` for a decision — the link the next
    event chains from."""
    row = (
        await session.execute(
            select(DecisionLedgerEvent.row_hash)
            .where(DecisionLedgerEvent.decision_id == decision_id)
            .order_by(DecisionLedgerEvent.seq.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return row


async def append_event(
    session: AsyncSession,
    *,
    decision_id: uuid.UUID,
    user_id: uuid.UUID | None,
    event_type: str,
    occurred_at: datetime,
    payload: dict[str, Any],
) -> DecisionLedgerEvent:
    """Append one immutable event, chaining its hash off the prior event for this
    decision. The only write path into the ledger."""
    prev_hash = await _latest_hash_for(session, decision_id)
    row_hash = canonical_hash(
        prev_hash=prev_hash,
        decision_id=decision_id,
        event_type=event_type,
        occurred_at=occurred_at,
        payload=payload,
    )
    event = DecisionLedgerEvent(
        id=uuid.uuid4(),
        decision_id=decision_id,
        user_id=user_id,
        event_type=event_type,
        occurred_at=occurred_at,
        payload=payload,
        prev_hash=prev_hash,
        row_hash=row_hash,
    )
    session.add(event)
    await session.flush()
    return event


async def get_for_decision(
    session: AsyncSession, decision_id: uuid.UUID
) -> list[DecisionLedgerEvent]:
    """All events for a decision in append order. Ownership (404) is enforced by
    the router from the events' copied `user_id`."""
    result = await session.execute(
        select(DecisionLedgerEvent)
        .where(DecisionLedgerEvent.decision_id == decision_id)
        .order_by(DecisionLedgerEvent.seq.asc())
    )
    return list(result.scalars().all())


async def list_for_user(
    session: AsyncSession, *, user_id: uuid.UUID | None, limit: int = 200
) -> list[DecisionLedgerEvent]:
    """Every ledger event in the requester scope (`user_id`), newest first. The
    filter is always applied — `user_id=None` selects the anonymous pool."""
    result = await session.execute(
        select(DecisionLedgerEvent)
        .where(DecisionLedgerEvent.user_id == user_id)
        .order_by(DecisionLedgerEvent.seq.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


def verify_chain(events: list[DecisionLedgerEvent]) -> dict[str, Any]:
    """Recompute the hash chain for a decision's events (seq order) and detect
    any break — this is what makes the ledger tamper-EVIDENT. An out-of-band edit
    that bypassed the immutability trigger (e.g. superuser direct-SQL) changes the
    derived `row_hash`, so the recomputed value won't match the stored one.

    Returns {ok, broken_at_seq, length}. `ok` is True for an empty chain.
    """
    expected_prev: str | None = None
    for ev in events:
        recomputed = canonical_hash(
            prev_hash=expected_prev,
            decision_id=ev.decision_id,
            event_type=ev.event_type,
            occurred_at=ev.occurred_at,
            payload=ev.payload,
        )
        if ev.prev_hash != expected_prev or ev.row_hash != recomputed:
            return {"ok": False, "broken_at_seq": ev.seq, "length": len(events)}
        expected_prev = ev.row_hash
    return {"ok": True, "broken_at_seq": None, "length": len(events)}
