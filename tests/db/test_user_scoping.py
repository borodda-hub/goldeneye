"""Phase B3a — query-layer per-user isolation (real DB, no HTTP/auth).

Proves the data-layer scoping capability directly against a migrated DB:
- list reads filter by `user_id` (a real id sees only its own rows; `None` sees
  the shared anonymous pool, never another user's);
- `replace_active`'s deactivate is scoped to the requester (the B3 landmine: an
  unscoped deactivate would flip *every other user's* active thesis);
- the calibration service aggregates only the requester's entries;
- the default `user_id=None` is behavior-preserving (today's anonymous pool).

This is the B3a acceptance gate (plan §6.A). It exercises real SQL `WHERE`
clauses, so it lives in tests/db (testcontainer), not the mocked apps/api suite.
"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from apps.api.models.orm.instruments import Instrument
from apps.api.models.orm.users import User
from apps.api.repos import journal as journal_repo
from apps.api.repos import paper_trades as trade_repo
from apps.api.repos import scenarios as scenario_repo
from apps.api.repos import theses as theses_repo
from apps.api.services import calibration as calib_svc
from apps.api.services import paper_engine

_THESIS_KW = dict(
    statement="s",
    supporting_evidence=[],
    contradicting_evidence=[],
    missing_data=[],
    conviction_pct=50,
)


@asynccontextmanager
async def _db(migrated_url):
    engine = create_async_engine(migrated_url)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            yield session
    finally:
        await engine.dispose()


async def _mk_user(session) -> User:
    u = User(clerk_user_id=f"user_{uuid.uuid4().hex}")
    session.add(u)
    await session.flush()
    return u


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


async def _mk_journal(session, instrument_id, *, user_id, hypothesis, resolved=None):
    data = {
        "hypothesis": hypothesis,
        "confidence_pct": 80,
        "user_id": user_id,
        "resolved_direction": resolved,
    }
    return await journal_repo.create(session, instrument_id, data)


# ── The landmine: replace_active must not cross-deactivate ──────────────────
@pytest.mark.asyncio
async def test_replace_active_isolation(migrated_url):
    async with _db(migrated_url) as s:
        a = await _mk_user(s)
        b = await _mk_user(s)

        ta = await theses_repo.replace_active(
            s, instrument_code="NG", user_id=a.id, **_THESIS_KW
        )
        await theses_repo.replace_active(
            s, instrument_code="NG", user_id=b.id, **_THESIS_KW
        )
        # B replaces their own active thesis — must touch ONLY B's row.
        tb2 = await theses_repo.replace_active(
            s, instrument_code="NG", user_id=b.id, **_THESIS_KW
        )
        await s.flush()

        # A's active thesis is untouched (the assertion the unscoped deactivate breaks).
        a_active = await theses_repo.get_active(s, instrument_code="NG", user_id=a.id)
        assert a_active is not None and a_active.id == ta.id and a_active.active is True

        # B has exactly the latest as active.
        b_active = await theses_repo.get_active(s, instrument_code="NG", user_id=b.id)
        assert b_active is not None and b_active.id == tb2.id

        # The anonymous (NULL) pool is its own single-active scope, independent of A/B.
        tn = await theses_repo.replace_active(
            s, instrument_code="NG", user_id=None, **_THESIS_KW
        )
        await s.flush()
        a_still = await theses_repo.get_active(s, instrument_code="NG", user_id=a.id)
        assert a_still is not None and a_still.id == ta.id and a_still.active is True
        anon = await theses_repo.get_active(s, instrument_code="NG", user_id=None)
        assert anon is not None and anon.id == tn.id


# ── List reads filter by scope (journal / scenarios / paper) ────────────────
@pytest.mark.asyncio
async def test_list_reads_scoped(migrated_url):
    async with _db(migrated_url) as s:
        a = await _mk_user(s)
        b = await _mk_user(s)
        inst = await _mk_instrument(s)

        # journal: A=2, B=1, anonymous=1
        await _mk_journal(s, inst.id, user_id=a.id, hypothesis="a1")
        await _mk_journal(s, inst.id, user_id=a.id, hypothesis="a2")
        await _mk_journal(s, inst.id, user_id=b.id, hypothesis="b1")
        await _mk_journal(s, inst.id, user_id=None, hypothesis="anon")
        # scenarios: A=1, B=1
        await scenario_repo.create(s, inst.id, "sa", [], {}, user_id=a.id)
        await scenario_repo.create(s, inst.id, "sb", [], {}, user_id=b.id)
        # paper: A=1, B=1
        await trade_repo.create(
            s, inst.id, {"side": "long", "size_contracts": 1, "entry_price": 3.0,
                         "status": "open", "user_id": a.id}
        )
        await trade_repo.create(
            s, inst.id, {"side": "short", "size_contracts": 1, "entry_price": 3.0,
                         "status": "open", "user_id": b.id}
        )
        await s.flush()

        # journal
        assert {r.hypothesis for r in await journal_repo.get_recent(
            s, instrument_id=inst.id, user_id=a.id)} == {"a1", "a2"}
        assert {r.hypothesis for r in await journal_repo.get_recent(
            s, instrument_id=inst.id, user_id=b.id)} == {"b1"}
        assert {r.hypothesis for r in await journal_repo.get_recent(
            s, instrument_id=inst.id, user_id=None)} == {"anon"}
        # scenarios — A sees only A's, never B's
        a_scn = await scenario_repo.get_recent(s, user_id=a.id)
        assert all(r.user_id == a.id for r in a_scn) and {r.name for r in a_scn} >= {"sa"}
        assert "sb" not in {r.name for r in a_scn}
        # paper
        a_trades = await trade_repo.list_trades(s, user_id=a.id)
        assert all(t.user_id == a.id for t in a_trades) and len(a_trades) == 1


# ── default user_id=None is behavior-preserving (anonymous pool) ────────────
@pytest.mark.asyncio
async def test_default_none_is_anonymous_pool(migrated_url):
    async with _db(migrated_url) as s:
        a = await _mk_user(s)
        inst = await _mk_instrument(s)
        await _mk_journal(s, inst.id, user_id=None, hypothesis="anon")
        await _mk_journal(s, inst.id, user_id=a.id, hypothesis="mine")
        await s.flush()

        # The current call convention (no user_id arg) == the anonymous NULL pool.
        default_rows = await journal_repo.get_recent(s, instrument_id=inst.id)
        assert {r.hypothesis for r in default_rows} == {"anon"}
        # ...and a signed-in user never sees the anonymous rows.
        a_rows = await journal_repo.get_recent(s, instrument_id=inst.id, user_id=a.id)
        assert {r.hypothesis for r in a_rows} == {"mine"}


# ── Service-layer scoping (calibration only counts the requester's entries) ──
@pytest.mark.asyncio
async def test_calibration_service_scoped(migrated_url):
    async with _db(migrated_url) as s:
        a = await _mk_user(s)
        b = await _mk_user(s)
        inst = await _mk_instrument(s)
        await _mk_journal(s, inst.id, user_id=a.id, hypothesis="a", resolved="hit")
        await _mk_journal(s, inst.id, user_id=b.id, hypothesis="b1", resolved="hit")
        await _mk_journal(s, inst.id, user_id=b.id, hypothesis="b2", resolved="miss")
        await s.flush()

        a_res = await calib_svc.compute_calibration(
            s, instrument_id=inst.id, instrument_code=inst.symbol, user_id=a.id
        )
        b_res = await calib_svc.compute_calibration(
            s, instrument_id=inst.id, instrument_code=inst.symbol, user_id=b.id
        )
        anon_res = await calib_svc.compute_calibration(
            s, instrument_id=inst.id, instrument_code=inst.symbol, user_id=None
        )
        assert a_res.total_entries == 1
        assert b_res.total_entries == 2
        assert anon_res.total_entries == 0


# ── Paper equity is scoped (P5/P6) ─────────────────────────────────────────
@pytest.mark.asyncio
async def test_equity_curve_scoped(migrated_url):
    async with _db(migrated_url) as s:
        a = await _mk_user(s)
        b = await _mk_user(s)
        inst = await _mk_instrument(s)
        # one closed trade each; different PnL
        for user, pnl in ((a, 100.0), (b, -50.0)):
            await trade_repo.create(s, inst.id, {
                "side": "long", "size_contracts": 1, "entry_price": 3.0,
                "exit_price": 3.1, "status": "closed", "outcome_pnl": pnl,
                "user_id": user.id,
            })
        await s.flush()

        eq_a = await paper_engine.current_equity(s, user_id=a.id)
        eq_b = await paper_engine.current_equity(s, user_id=b.id)
        eq_anon = await paper_engine.current_equity(s, user_id=None)
        # A's equity reflects only A's +100; B's only -50; anonymous sees neither.
        assert eq_a - eq_anon == pytest.approx(100.0)
        assert eq_b - eq_anon == pytest.approx(-50.0)
