"""Phase B2 — desk skill-vs-luck verdict, real-DB honesty lock.

THE honesty regression for the skill-vs-luck verdict, deliberately placed in the
gated `tests/db` suite (it runs in CI's `db-tests` job, not the fast mocked one)
so it guards the real query path end-to-end, not a hand-built mock.

The claim being locked: the verdict (Wilson 95% CI on directional hit-rate vs the
0.50 chance baseline) **correctly refuses to call noise skill**. A literal
coin-flip desk — exactly 50% hits over a large sample — must resolve to ``luck``,
never ``skill``; and a desk whose hit-rate genuinely clears chance must resolve to
``skill``. If this ever flips, the platform would be crowning luck as skill — the
exact dishonesty the whole calibration story exists to prevent.

Real `select ... where resolved_direction in (hit,miss)` against persisted journal
rows, so it lives in tests/db (testcontainer), not the mocked apps/api suite.
"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import apps.api.models.orm.theses  # noqa: F401  (registers journal's FK target)
from apps.api.models.orm.instruments import Instrument
from apps.api.models.orm.journal import UserDecisionJournal
from apps.api.services.desk_calibration import compute_desk_calibration


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


async def _seed_desk(session, instrument_id, user_id, *, hits: int, misses: int) -> None:
    """Insert `hits` resolved-hit + `misses` resolved-miss decisions for a desk.

    Outcomes are stamped directly (this test is about the *verdict over resolved
    rows*, not the resolution engine — that has its own lock).
    """
    for i in range(hits + misses):
        outcome = "hit" if i < hits else "miss"
        session.add(
            UserDecisionJournal(
                id=uuid.uuid4(),
                created_at=datetime(2026, 1, 1),
                user_id=user_id,
                instrument_id=instrument_id,
                hypothesis=f"verdict-lock {user_id} {i}",
                evidence=[],
                confidence_pct=50,
                predicted_direction="bullish",
                horizon_days=10,
                threshold_pct=1.0,
                anchor_price=100.0,
                resolved_direction=outcome,
                auto_resolved=True,
            )
        )
    await session.flush()


@pytest.mark.asyncio
async def test_coinflip_desk_reads_luck_and_real_edge_reads_skill(migrated_url):
    async with _db(migrated_url) as s:
        inst = await _mk_instrument(s)
        coin = uuid.uuid4()   # the luck baseline — exactly 50% hits
        edged = uuid.uuid4()  # a hit-rate that genuinely clears chance
        # 30/30 = 50% over n=60 → CI straddles 0.50.
        await _seed_desk(s, inst.id, coin, hits=30, misses=30)
        # 45/15 = 75% over n=60 → CI lower bound clears 0.50.
        await _seed_desk(s, inst.id, edged, hits=45, misses=15)
        await s.commit()

        out = await compute_desk_calibration(s)
        by = {a["user_id"]: a for a in out["analysts"]}

        # ── THE honesty lock: noise is never crowned skill. ──
        coin_row = by[str(coin)]
        assert coin_row["n"] == 60
        assert coin_row["verdict"] == "luck"
        assert coin_row["wilson_low"] < 0.5 < coin_row["wilson_high"]

        # The genuine edge IS recognized (the test isn't just "everything is luck").
        edged_row = by[str(edged)]
        assert edged_row["n"] == 60
        assert edged_row["verdict"] == "skill"
        assert edged_row["wilson_low"] > 0.5

        assert out["baseline"] == 0.5


@pytest.mark.asyncio
async def test_thin_record_is_insufficient_not_skill(migrated_url):
    """A perfect-but-tiny record (5/5) is `insufficient`, never `skill`."""
    async with _db(migrated_url) as s:
        inst = await _mk_instrument(s)
        thin = uuid.uuid4()
        await _seed_desk(s, inst.id, thin, hits=5, misses=0)  # n=5 < gate
        await s.commit()

        out = await compute_desk_calibration(s)
        row = next(a for a in out["analysts"] if a["user_id"] == str(thin))
        assert row["n"] == 5
        assert row["qualifies"] is False
        assert row["verdict"] == "insufficient"
        assert row["wilson_low"] is None and row["wilson_high"] is None
