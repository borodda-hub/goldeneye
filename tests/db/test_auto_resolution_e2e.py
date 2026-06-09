"""Phase B1 — auto-resolution engine lock (real DB, no HTTP/scheduler).

This is the *engine proof*, kept deliberately separate from the showcase seed:
it pins the behavior the scheduler depends on, against a controlled set of real
`price_bars` rather than the demo cohort. If any of these break, the calibration
ledger the scheduler compounds is silently wrong.

Locks (plan §6 / §11):
- a decision whose horizon has elapsed resolves to the CORRECT hit/miss from the
  real anchor→realized move (bullish into an up move = hit; bearish = miss);
- it is IDEMPOTENT — a second tick resolves 0 and overwrites nothing
  (`resolved_at` is byte-for-byte unchanged);
- a manually-marked decision is NEVER touched (the `resolved_direction IS NULL`
  guard), so analyst intent always wins over the engine.

Real `WHERE`/ordering against the front-month/price_bars path, so it lives in
tests/db (testcontainer), not the mocked apps/api suite.
"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import apps.api.models.orm.theses  # noqa: F401  (registers journal's FK target)
from apps.api.models.orm.contracts import Contract
from apps.api.models.orm.instruments import Instrument
from apps.api.models.orm.journal import UserDecisionJournal
from apps.api.models.orm.prices import PriceBar
from apps.api.services.auto_resolution import resolve_open_decisions

# A controlled anchor→target window, fully elapsed by `_NOW`.
_ANCHOR = date(2026, 1, 5)
_HORIZON = 14
_TARGET = date(2026, 1, 19)   # _ANCHOR + 14d
_NOW = datetime(2026, 2, 1)   # well past the target
_ANCHOR_CLOSE = 100.0
_TARGET_CLOSE = 106.0         # a clean +6% up move


@asynccontextmanager
async def _db(migrated_url):
    engine = create_async_engine(migrated_url)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            yield session
    finally:
        await engine.dispose()


async def _mk_instrument(session) -> Instrument:
    inst = Instrument(
        symbol=f"T{uuid.uuid4().hex[:8].upper()}",
        name="Test Instrument",
        exchange="TEST",
        unit="u",
        contract_size=1,
        tick_size=0.01,
    )
    session.add(inst)
    await session.flush()
    return inst


async def _mk_front_contract(session, instrument_id) -> Contract:
    c = Contract(
        instrument_id=instrument_id,
        contract_code=f"C{uuid.uuid4().hex[:6].upper()}",
        expiry_date=date(2027, 1, 1),
        is_front_month=True,
    )
    session.add(c)
    await session.flush()
    return c


async def _mk_bar(session, contract_id, d: date, close: float) -> None:
    # ts is naive (TIMESTAMP WITHOUT TIME ZONE); midnight matches the engine's
    # naive-UTC comparison and the demo seed's created_at convention.
    session.add(
        PriceBar(
            ts=datetime(d.year, d.month, d.day),
            contract_id=contract_id,
            resolution="1d",
            open=close,
            high=close,
            low=close,
            close=close,
            source="yahoo_delayed",
        )
    )
    await session.flush()


async def _mk_decision(
    session,
    instrument_id,
    *,
    direction: str,
    resolved: str | None = None,
    auto: bool = False,
) -> UserDecisionJournal:
    d = UserDecisionJournal(
        id=uuid.uuid4(),
        created_at=datetime(_ANCHOR.year, _ANCHOR.month, _ANCHOR.day),
        user_id=None,
        instrument_id=instrument_id,
        hypothesis=f"lock-test {direction}",
        evidence=[],
        confidence_pct=80,
        predicted_direction=direction,
        horizon_days=_HORIZON,
        threshold_pct=1.0,          # 1% deadband; the +6% move clears it
        anchor_price=_ANCHOR_CLOSE,
        resolved_direction=resolved,
        auto_resolved=auto,
    )
    session.add(d)
    await session.flush()
    return d


@pytest.mark.asyncio
async def test_resolves_correct_outcome_then_idempotent_and_manual_safe(migrated_url):
    async with _db(migrated_url) as s:
        inst = await _mk_instrument(s)
        front = await _mk_front_contract(s, inst.id)
        await _mk_bar(s, front.id, _ANCHOR, _ANCHOR_CLOSE)
        await _mk_bar(s, front.id, _TARGET, _TARGET_CLOSE)

        bull = await _mk_decision(s, inst.id, direction="bullish")  # into +6% → hit
        bear = await _mk_decision(s, inst.id, direction="bearish")  # against +6% → miss
        # Manually marked the WRONG way on purpose: if the engine touched it, it
        # would flip to "miss". It must stay exactly as the analyst left it.
        manual = await _mk_decision(
            s, inst.id, direction="bearish", resolved="hit", auto=False
        )
        await s.commit()

        # ── First tick: resolves the two open decisions to the real outcomes ──
        res = await resolve_open_decisions(s, now=_NOW)
        await s.commit()

        assert res.resolved == 2
        assert res.by_outcome == {"hit": 1, "miss": 1}

        await s.refresh(bull)
        await s.refresh(bear)
        await s.refresh(manual)
        assert bull.resolved_direction == "hit" and bull.auto_resolved is True
        assert bull.resolved_at is not None
        assert bear.resolved_direction == "miss" and bear.auto_resolved is True
        # Manual mark untouched (engine never overwrites a non-NULL resolution).
        assert manual.resolved_direction == "hit" and manual.auto_resolved is False

        bull_stamp = bull.resolved_at

        # ── Second tick: idempotent — nothing left to resolve, nothing rewritten ──
        res2 = await resolve_open_decisions(s, now=_NOW)
        await s.commit()

        assert res2.resolved == 0
        assert res2.by_outcome == {}

        await s.refresh(bull)
        await s.refresh(manual)
        assert bull.resolved_direction == "hit"
        assert bull.resolved_at == bull_stamp  # not re-stamped
        assert manual.resolved_direction == "hit" and manual.auto_resolved is False


@pytest.mark.asyncio
async def test_unelapsed_horizon_stays_pending(migrated_url):
    """A decision whose horizon has NOT elapsed is left open (look-ahead safe)."""
    async with _db(migrated_url) as s:
        inst = await _mk_instrument(s)
        front = await _mk_front_contract(s, inst.id)
        await _mk_bar(s, front.id, _ANCHOR, _ANCHOR_CLOSE)
        await _mk_bar(s, front.id, _TARGET, _TARGET_CLOSE)
        d = await _mk_decision(s, inst.id, direction="bullish")
        await s.commit()

        # `now` is BEFORE the target → the horizon hasn't elapsed yet.
        res = await resolve_open_decisions(s, now=datetime(2026, 1, 10))
        await s.commit()

        assert res.resolved == 0
        assert res.still_pending == 1
        await s.refresh(d)
        assert d.resolved_direction is None and d.auto_resolved is False
