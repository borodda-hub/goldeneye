"""Phase B4 — decision/audit ledger read API.

The immutable "at the moment of decision, here is exactly what you knew" view.
Read-only (the ledger is append-only; appends happen on the journal/resolution
paths). Scoped by `user_id` with by-id 404 ownership — the B3 isolation invariant.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.auth.deps import get_optional_user
from apps.api.db.session import get_db
from apps.api.models.orm.ledger import DecisionLedgerEvent
from apps.api.models.orm.users import User
from apps.api.repos import ledger as ledger_repo

router = APIRouter(prefix="/v1/ledger", tags=["ledger"])


class LedgerEventOut(BaseModel):
    seq: int
    decision_id: str
    event_type: str
    occurred_at: datetime
    recorded_at: datetime
    source: str
    payload: dict[str, Any]
    prev_hash: str | None
    row_hash: str


class LedgerDecisionOut(BaseModel):
    decision_id: str
    events: list[LedgerEventOut]
    chain_ok: bool  # hash-chain integrity — tamper-evidence
    broken_at_seq: int | None


class LedgerListOut(BaseModel):
    decisions: list[LedgerDecisionOut]


def _event_out(ev: DecisionLedgerEvent) -> LedgerEventOut:
    return LedgerEventOut(
        seq=ev.seq,
        decision_id=str(ev.decision_id),
        event_type=ev.event_type,
        occurred_at=ev.occurred_at,
        recorded_at=ev.recorded_at,
        source=ev.source,
        payload=ev.payload,
        prev_hash=ev.prev_hash,
        row_hash=ev.row_hash,
    )


def _decision_out(
    decision_id: uuid.UUID, events: list[DecisionLedgerEvent]
) -> LedgerDecisionOut:
    chain = ledger_repo.verify_chain(events)
    return LedgerDecisionOut(
        decision_id=str(decision_id),
        events=[_event_out(e) for e in events],
        chain_ok=bool(chain["ok"]),
        broken_at_seq=chain["broken_at_seq"],
    )


@router.get("", response_model=LedgerListOut)
async def get_ledger(
    session: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_optional_user),
) -> LedgerListOut:
    """The requester's decision ledger — each decision with its immutable event
    timeline and a chain-integrity flag. Scoped to the requester (`user_id`)."""
    scope = user.id if user else None
    events = await ledger_repo.list_for_user(session, user_id=scope)
    # Group by decision, preserving most-recent-first decision order.
    groups: dict[uuid.UUID, list[DecisionLedgerEvent]] = {}
    order: list[uuid.UUID] = []
    for ev in events:  # newest first
        if ev.decision_id not in groups:
            groups[ev.decision_id] = []
            order.append(ev.decision_id)
        groups[ev.decision_id].append(ev)
    decisions = [
        _decision_out(did, sorted(groups[did], key=lambda e: e.seq))
        for did in order
    ]
    return LedgerListOut(decisions=decisions)


@router.get("/{decision_id}", response_model=LedgerDecisionOut)
async def get_ledger_decision(
    decision_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_optional_user),
) -> LedgerDecisionOut:
    """One decision's full immutable record. 404 if it has no ledger (e.g. a
    pre-B4 decision — no record exists by design) or is owned by another user
    (ownership leak-proofing, mirroring the journal)."""
    scope = user.id if user else None
    events = await ledger_repo.get_for_decision(session, decision_id)
    if not events or events[0].user_id != scope:
        raise HTTPException(status_code=404, detail="No ledger for this decision")
    return _decision_out(decision_id, events)
