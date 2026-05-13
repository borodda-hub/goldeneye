"""Phase 12 Step 1 — repo-layer tests for theses.

Unit-level — uses a fake AsyncSession to verify behavior of replace_active
(deactivate + insert) and input validation. End-to-end DB round-trip is
covered by the route tests in test_thesis_endpoints.py (Step 2).
"""
from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock

import pytest

from apps.api.models.orm.theses import Thesis
from apps.api.repos import theses as repo


def _thesis(
    *,
    statement: str = "Cold snap sustains storage draws.",
    conviction: int = 70,
    active: bool = True,
) -> Thesis:
    t = Thesis(
        id=uuid.uuid4(),
        instrument_code="NG",
        statement=statement,
        supporting_evidence=[{"factor": "weather", "weight": 0.5, "note": ""}],
        contradicting_evidence=[],
        missing_data=["EIA Weekly Storage"],
        conviction_pct=conviction,
        active=active,
    )
    return t


def _fake_session_with_scalar(scalar_return: Any) -> AsyncMock:
    """Build an AsyncMock that returns scalar_return from .scalar_one_or_none()."""
    session = AsyncMock()
    result = AsyncMock()
    result.scalar_one_or_none = lambda: scalar_return
    session.execute = AsyncMock(return_value=result)
    session.add = lambda *args, **kwargs: None
    session.flush = AsyncMock(return_value=None)
    return session


# ── replace_active validation ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_replace_active_rejects_conviction_out_of_range():
    session = AsyncMock()
    with pytest.raises(ValueError, match="conviction_pct"):
        await repo.replace_active(
            session,
            instrument_code="NG",
            statement="x",
            supporting_evidence=[],
            contradicting_evidence=[],
            missing_data=[],
            conviction_pct=150,
        )


@pytest.mark.asyncio
async def test_replace_active_rejects_negative_conviction():
    session = AsyncMock()
    with pytest.raises(ValueError, match="conviction_pct"):
        await repo.replace_active(
            session,
            instrument_code="NG",
            statement="x",
            supporting_evidence=[],
            contradicting_evidence=[],
            missing_data=[],
            conviction_pct=-1,
        )


@pytest.mark.asyncio
async def test_replace_active_rejects_empty_statement():
    session = AsyncMock()
    with pytest.raises(ValueError, match="statement must be non-empty"):
        await repo.replace_active(
            session,
            instrument_code="NG",
            statement="   ",
            supporting_evidence=[],
            contradicting_evidence=[],
            missing_data=[],
            conviction_pct=50,
        )


# ── replace_active happy path ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_replace_active_issues_update_then_insert():
    """First execute() runs the UPDATE deactivating any existing active row;
    then session.add() inserts the new thesis; finally a flush is awaited."""
    session = AsyncMock()
    session.execute = AsyncMock(return_value=AsyncMock())
    added: list[Thesis] = []
    session.add = lambda obj: added.append(obj)
    session.flush = AsyncMock(return_value=None)

    fresh = await repo.replace_active(
        session,
        instrument_code="NG",
        statement="Storage draws exceed five-year average.",
        supporting_evidence=[{"factor": "weather", "weight": 0.6, "note": ""}],
        contradicting_evidence=[{"factor": "lng_export_dip", "weight": 0.2, "note": ""}],
        missing_data=["EIA Weekly Storage"],
        conviction_pct=72,
    )

    # Deactivation UPDATE ran exactly once.
    assert session.execute.await_count == 1
    # New row was added and flushed.
    assert len(added) == 1
    assert added[0] is fresh
    session.flush.assert_awaited_once()
    # Field round-trip.
    assert fresh.instrument_code == "NG"
    assert fresh.statement == "Storage draws exceed five-year average."
    assert fresh.conviction_pct == 72
    assert fresh.active is True
    assert fresh.supporting_evidence[0]["factor"] == "weather"


@pytest.mark.asyncio
async def test_replace_active_strips_statement_whitespace():
    session = AsyncMock()
    session.execute = AsyncMock(return_value=AsyncMock())
    added: list[Thesis] = []
    session.add = lambda obj: added.append(obj)
    session.flush = AsyncMock(return_value=None)

    fresh = await repo.replace_active(
        session,
        instrument_code="NG",
        statement="  Cold snap.  \n",
        supporting_evidence=[],
        contradicting_evidence=[],
        missing_data=[],
        conviction_pct=50,
    )
    assert fresh.statement == "Cold snap."


# ── get_active / get_by_id ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_active_returns_thesis_when_present():
    expected = _thesis()
    session = _fake_session_with_scalar(expected)
    result = await repo.get_active(session, instrument_code="NG")
    assert result is expected


@pytest.mark.asyncio
async def test_get_active_returns_none_when_absent():
    session = _fake_session_with_scalar(None)
    result = await repo.get_active(session, instrument_code="NG")
    assert result is None


@pytest.mark.asyncio
async def test_get_by_id_returns_thesis():
    expected = _thesis()
    session = _fake_session_with_scalar(expected)
    result = await repo.get_by_id(session, expected.id)
    assert result is expected


# ── patch_active ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_patch_active_updates_allowed_fields():
    t = _thesis(conviction=50)
    session = AsyncMock()
    session.flush = AsyncMock(return_value=None)

    patched = await repo.patch_active(
        session,
        t,
        {
            "statement": "Updated statement.",
            "conviction_pct": 85,
            "missing_data": ["new item"],
        },
    )
    assert patched.statement == "Updated statement."
    assert patched.conviction_pct == 85
    assert patched.missing_data == ["new item"]


@pytest.mark.asyncio
async def test_patch_active_ignores_unknown_fields():
    t = _thesis()
    session = AsyncMock()
    session.flush = AsyncMock(return_value=None)

    await repo.patch_active(
        session,
        t,
        {"active": False, "id": uuid.uuid4(), "statement": "Allowed."},
    )
    # active and id are not in the allow-list; only statement applied.
    assert t.statement == "Allowed."
    assert t.active is True  # unchanged


@pytest.mark.asyncio
async def test_patch_active_rejects_invalid_conviction():
    t = _thesis()
    session = AsyncMock()
    with pytest.raises(ValueError, match="conviction_pct"):
        await repo.patch_active(session, t, {"conviction_pct": 150})


@pytest.mark.asyncio
async def test_patch_active_rejects_empty_statement():
    t = _thesis()
    session = AsyncMock()
    with pytest.raises(ValueError, match="statement must be non-empty"):
        await repo.patch_active(session, t, {"statement": "  "})
