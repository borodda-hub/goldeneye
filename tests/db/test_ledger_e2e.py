"""Phase B4 — decision/audit ledger immutability + tamper-evidence locks.

These are the close-out guarantees for the ledger, demonstrated against a real
migrated DB (testcontainer), so they execute in the CI `db-tests` job:

- BAR 1: the immutability trigger BITES — UPDATE and DELETE both raise at the DB
  level (not "the service doesn't try"; the database rejects the mutation).
- BAR 2: the hash chain DETECTS tampering — an edit that bypasses the trigger
  (superuser DISABLE TRIGGER) is caught by chain verification.
- BAR 3: the source CHECK blocks a non-live (fabricated/backfilled) event.
- BAR 4: lifecycle append + chain linkage (created → resolved).
"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import apps.api.models.orm.theses  # noqa: F401  (FK target registration)
from apps.api.models.orm.instruments import Instrument
from apps.api.models.orm.journal import UserDecisionJournal
from apps.api.models.orm.ledger import DecisionLedgerEvent
from apps.api.repos import ledger as ledger_repo


@asynccontextmanager
async def _db(migrated_url):
    engine = create_async_engine(migrated_url)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            yield session
    finally:
        await engine.dispose()


async def _mk_decision(session) -> UserDecisionJournal:
    inst = Instrument(
        symbol=f"L{uuid.uuid4().hex[:8].upper()}", name="t", exchange="T",
        unit="u", contract_size=1, tick_size=0.01,
    )
    session.add(inst)
    await session.flush()
    d = UserDecisionJournal(
        # created_at is a TIMESTAMP WITHOUT TIME ZONE column (naive) — match it.
        id=uuid.uuid4(), created_at=datetime(2026, 1, 1),
        user_id=None, instrument_id=inst.id, hypothesis="ledger test",
        evidence=[], confidence_pct=60, predicted_direction="bullish",
        horizon_days=10, threshold_pct=1.0, anchor_price=100.0,
    )
    session.add(d)
    await session.flush()
    return d


async def _append(session, decision, event_type="created", payload=None):
    return await ledger_repo.append_event(
        session, decision_id=decision.id, user_id=decision.user_id,
        event_type=event_type, occurred_at=datetime.now(UTC),
        payload=payload or {"k": "v"},
    )


# ── BAR 1: the trigger bites — UPDATE and DELETE raise at the DB level ──────────
@pytest.mark.asyncio
async def test_update_raises_at_db_level(migrated_url):
    async with _db(migrated_url) as s:
        d = await _mk_decision(s)
        ev = await _append(s, d)
        await s.commit()
        ev_id = ev.id

    async with _db(migrated_url) as s:
        with pytest.raises(Exception) as exc:
            await s.execute(
                text("UPDATE decision_ledger_events SET row_hash = 'x' WHERE id = :i"),
                {"i": ev_id},
            )
        assert "append-only" in str(exc.value).lower()

    # The row is unchanged.
    async with _db(migrated_url) as s:
        events = await ledger_repo.get_for_decision(s, (await _row_decision(s, ev_id)))
        assert events and events[0].row_hash != "x"


@pytest.mark.asyncio
async def test_delete_raises_at_db_level(migrated_url):
    async with _db(migrated_url) as s:
        d = await _mk_decision(s)
        ev = await _append(s, d)
        await s.commit()
        ev_id, did = ev.id, d.id

    async with _db(migrated_url) as s:
        with pytest.raises(Exception) as exc:
            await s.execute(
                text("DELETE FROM decision_ledger_events WHERE id = :i"), {"i": ev_id}
            )
        assert "append-only" in str(exc.value).lower()

    async with _db(migrated_url) as s:
        assert len(await ledger_repo.get_for_decision(s, did)) == 1


async def _row_decision(session, ev_id):
    return (
        await session.execute(
            text("SELECT decision_id FROM decision_ledger_events WHERE id = :i"),
            {"i": ev_id},
        )
    ).scalar_one()


# ── BAR 2: the hash chain detects tampering (edit that bypasses the trigger) ────
@pytest.mark.asyncio
async def test_hash_chain_detects_tampering(migrated_url):
    async with _db(migrated_url) as s:
        d = await _mk_decision(s)
        await _append(s, d, "created", {"hypothesis": "original"})
        await _append(s, d, "resolved", {"outcome": "hit"})
        await s.commit()
        did = d.id

    # Intact chain verifies.
    async with _db(migrated_url) as s:
        assert ledger_repo.verify_chain(await ledger_repo.get_for_decision(s, did))["ok"]

    # Tamper a payload by BYPASSING the immutability trigger (the superuser case).
    async with _db(migrated_url) as s:
        await s.execute(text(
            "ALTER TABLE decision_ledger_events DISABLE TRIGGER decision_ledger_events_no_mutate"))
        await s.execute(
            text("UPDATE decision_ledger_events SET payload = '{\"outcome\": \"miss\"}' "
                 "WHERE decision_id = :d AND event_type = 'resolved'"),
            {"d": did},
        )
        await s.execute(text(
            "ALTER TABLE decision_ledger_events ENABLE TRIGGER decision_ledger_events_no_mutate"))
        await s.commit()

    # Verification now FAILS — that is the tamper-evidence.
    async with _db(migrated_url) as s:
        events = await ledger_repo.get_for_decision(s, did)
        result = ledger_repo.verify_chain(events)
        assert result["ok"] is False
        assert result["broken_at_seq"] is not None


# ── BAR 3: the source CHECK blocks a non-live (fabricated) event ────────────────
@pytest.mark.asyncio
async def test_source_check_blocks_backfill(migrated_url):
    async with _db(migrated_url) as s:
        d = await _mk_decision(s)
        await s.commit()
        did, uid = d.id, d.user_id

    async with _db(migrated_url) as s:
        s.add(DecisionLedgerEvent(
            id=uuid.uuid4(), decision_id=did, user_id=uid, event_type="created",
            occurred_at=datetime.now(UTC), payload={}, prev_hash=None,
            row_hash="h", source="backfill",
        ))
        with pytest.raises(Exception) as exc:
            await s.flush()
        assert "ck_ledger_source_live" in str(exc.value) or "check constraint" in str(exc.value).lower()


# ── BAR 4: lifecycle append + chain linkage ────────────────────────────────────
@pytest.mark.asyncio
async def test_lifecycle_append_and_linkage(migrated_url):
    async with _db(migrated_url) as s:
        d = await _mk_decision(s)
        e1 = await _append(s, d, "created", {"a": 1})
        e2 = await _append(s, d, "resolved", {"b": 2})
        await s.commit()
        did = d.id
        e1_hash = e1.row_hash

    async with _db(migrated_url) as s:
        events = await ledger_repo.get_for_decision(s, did)
        assert [e.event_type for e in events] == ["created", "resolved"]
        assert events[0].prev_hash is None
        assert events[1].prev_hash == e1_hash  # chained
        assert ledger_repo.verify_chain(events)["ok"]
        assert events[0].source == "live"  # default, only valid value
