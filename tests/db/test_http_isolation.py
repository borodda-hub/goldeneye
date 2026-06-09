"""Phase B3b — §6.B end-to-end HTTP isolation matrix (authed A vs. B).

Drives the real FastAPI app over httpx against a migrated testcontainer DB, with
`get_db` overridden to the container and `get_optional_user` overridden to return
user A, user B, or None (anonymous). Proves, over HTTP, that a signed-in user can
read/modify only their own journal/theses/scenarios/paper — and that the anonymous
demo path still works. This is the B3b acceptance gate; it runs in the CI `db-tests`
job, so removing an ownership check turns CI red (see test_replace_active_isolation
for the same red→green discipline).
"""
from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from apps.api.auth.deps import get_optional_user
from apps.api.db.session import get_db
from apps.api.models.orm.instruments import Instrument
from apps.api.models.orm.users import User
from apps.api.repos import paper_trades as trade_repo
from apps.api.repos import scenarios as scenario_repo
from apps.api.src.main import app


@pytest_asyncio.fixture
async def ctx(migrated_url):
    engine = create_async_engine(migrated_url)
    sm = async_sessionmaker(engine, expire_on_commit=False)

    async def _override_get_db():
        async with sm() as s:
            yield s

    app.dependency_overrides[get_db] = _override_get_db

    # Two real users + one instrument (unique, committed).
    async with sm() as s:
        a = User(clerk_user_id=f"A_{uuid.uuid4().hex}")
        b = User(clerk_user_id=f"B_{uuid.uuid4().hex}")
        inst = Instrument(
            symbol=f"X{uuid.uuid4().hex[:8].upper()}", name="t", exchange="T",
            unit="u", contract_size=1, tick_size=0.01,
        )
        s.add_all([a, b, inst])
        await s.commit()
        a_id, b_id, inst_id, sym = a.id, b.id, inst.id, inst.symbol

    def as_user(uid: uuid.UUID | None) -> None:
        # Transient User is enough — endpoints only read user.id.
        app.dependency_overrides[get_optional_user] = (
            (lambda: None) if uid is None else (lambda: User(id=uid, clerk_user_id="x"))
        )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, as_user, sm, a_id, b_id, inst_id, sym

    app.dependency_overrides.clear()


# ── Journal: create as A; B can't list/read/modify it; anonymous can't either ──
@pytest.mark.asyncio
async def test_journal_http_isolation(ctx):
    client, as_user, _sm, a_id, b_id, _inst_id, sym = ctx

    as_user(a_id)
    r = await client.post("/v1/journal", json={
        "instrument": sym, "hypothesis": "A's private hypothesis", "confidence_pct": 70})
    assert r.status_code == 200, r.text
    entry_id = r.json()["id"]

    # A sees it (list + by-id).
    assert any(e["id"] == entry_id for e in (await client.get("/v1/journal")).json()["entries"])
    assert (await client.get(f"/v1/journal/{entry_id}")).status_code == 200

    # B: not in list, 404 by-id, 404 on patch — and A's row unchanged.
    as_user(b_id)
    assert all(e["id"] != entry_id for e in (await client.get("/v1/journal")).json()["entries"])
    assert (await client.get(f"/v1/journal/{entry_id}")).status_code == 404
    assert (await client.patch(f"/v1/journal/{entry_id}",
                               json={"reflection": "hacked"})).status_code == 404

    # Anonymous can't reach A's entry either.
    as_user(None)
    assert (await client.get(f"/v1/journal/{entry_id}")).status_code == 404

    as_user(a_id)
    assert (await client.get(f"/v1/journal/{entry_id}")).json()["reflection"] is None


# ── Thesis: the landmine end-to-end + by-id ownership ──────────────────────────
@pytest.mark.asyncio
async def test_thesis_http_isolation(ctx):
    client, as_user, _sm, a_id, b_id, _inst_id, _sym = ctx
    code = f"IC{uuid.uuid4().hex[:6].upper()}"  # fresh instrument_code (string, no FK)

    as_user(a_id)
    r = await client.post("/v1/thesis", json={
        "instrument_code": code, "statement": "A's thesis", "conviction_pct": 60})
    assert r.status_code == 200, r.text
    a_thesis_id = r.json()["id"]
    assert (await client.get(f"/v1/thesis/current?instrument_code={code}")).json()["id"] == a_thesis_id

    # B has no thesis here, and creating one must NOT deactivate A's (the landmine).
    as_user(b_id)
    assert (await client.get(f"/v1/thesis/current?instrument_code={code}")).status_code == 404
    assert (await client.post("/v1/thesis", json={
        "instrument_code": code, "statement": "B's thesis", "conviction_pct": 50})).status_code == 200

    as_user(a_id)
    a_current = await client.get(f"/v1/thesis/current?instrument_code={code}")
    assert a_current.status_code == 200 and a_current.json()["id"] == a_thesis_id  # still active

    # B cannot critique or patch A's thesis (by-id ownership → 404).
    as_user(b_id)
    assert (await client.post(f"/v1/thesis/{a_thesis_id}/critique")).status_code == 404
    assert (await client.patch(f"/v1/thesis/{a_thesis_id}",
                               json={"conviction_pct": 1})).status_code == 404


# ── Scenarios: seeded per user; list scoping + by-id ownership over HTTP ────────
@pytest.mark.asyncio
async def test_scenario_http_isolation(ctx):
    client, as_user, sm, a_id, b_id, inst_id, _sym = ctx
    async with sm() as s:
        a_run = await scenario_repo.create(s, instrument_id=inst_id, name="A run",
                                           shocks=[], result={}, user_id=a_id)
        await scenario_repo.create(s, instrument_id=inst_id, name="B run",
                                   shocks=[], result={}, user_id=b_id)
        await s.commit()
        a_run_id = str(a_run.id)

    as_user(a_id)
    assert (await client.get(f"/v1/scenarios/runs/{a_run_id}")).status_code == 200
    assert any(x["run_id"] == a_run_id for x in (await client.get("/v1/scenarios/runs")).json()["runs"])

    as_user(b_id)
    assert (await client.get(f"/v1/scenarios/runs/{a_run_id}")).status_code == 404
    assert all(x["run_id"] != a_run_id for x in (await client.get("/v1/scenarios/runs")).json()["runs"])
    # explain-scenario by-id is also ownership-gated.
    assert (await client.post("/v1/explain/scenario", json={"run_id": a_run_id})).status_code == 404


# ── Paper trades: seeded per user; list scoping + by-id + close ownership ───────
@pytest.mark.asyncio
async def test_paper_http_isolation(ctx):
    client, as_user, sm, a_id, b_id, inst_id, _sym = ctx
    async with sm() as s:
        a_trade = await trade_repo.create(s, inst_id, {
            "side": "long", "size_contracts": 1, "entry_price": 3.0,
            "status": "open", "user_id": a_id})
        await trade_repo.create(s, inst_id, {
            "side": "short", "size_contracts": 1, "entry_price": 3.0,
            "status": "open", "user_id": b_id})
        await s.commit()
        a_trade_id = str(a_trade.id)

    as_user(a_id)
    assert (await client.get(f"/v1/paper-trades/{a_trade_id}")).status_code == 200
    assert {t["id"] for t in (await client.get("/v1/paper-trades")).json()["trades"]} == {a_trade_id}

    as_user(b_id)
    assert (await client.get(f"/v1/paper-trades/{a_trade_id}")).status_code == 404
    assert all(t["id"] != a_trade_id for t in (await client.get("/v1/paper-trades")).json()["trades"])
    # B cannot close A's trade.
    assert (await client.post(f"/v1/paper-trades/{a_trade_id}/close",
                              json={"exit_price": 3.5})).status_code == 404


# ── Admin/desk gating: denied to anonymous when accounts are configured ────────
@pytest.mark.asyncio
async def test_admin_desk_gating_when_clerk_configured(ctx, monkeypatch):
    client, as_user, _sm, a_id, _b, _inst_id, _sym = ctx
    import apps.api.auth.deps as deps
    monkeypatch.setattr(deps, "clerk_configured", lambda: True)

    # Anonymous is denied (401) on the admin + desk surfaces.
    as_user(None)
    assert (await client.get("/v1/admin/alerts")).status_code == 401
    assert (await client.get("/v1/calibration/desk")).status_code == 401

    # A signed-in user is allowed (B3b only stops anonymous; visibility model is B2).
    as_user(a_id)
    assert (await client.get("/v1/admin/alerts")).status_code == 200
    assert (await client.get("/v1/calibration/desk")).status_code == 200


# ── Anonymous demo path still works (the seeded NULL pool is readable) ──────────
@pytest.mark.asyncio
async def test_anonymous_demo_path_survives(ctx):
    client, as_user, sm, _a, _b, inst_id, sym = ctx
    # An anonymous (user_id NULL) journal entry, created via the anonymous HTTP path.
    as_user(None)
    r = await client.post("/v1/journal", json={
        "instrument": sym, "hypothesis": "anon demo entry", "confidence_pct": 50})
    assert r.status_code == 200, r.text
    anon_id = r.json()["id"]
    # Anonymous reads it back (list + by-id) — the demo path is intact.
    assert any(e["id"] == anon_id for e in (await client.get("/v1/journal")).json()["entries"])
    assert (await client.get(f"/v1/journal/{anon_id}")).status_code == 200
    # A signed-in user does NOT see the anonymous entry.
    as_user(_a)
    assert (await client.get(f"/v1/journal/{anon_id}")).status_code == 404
