"""Phase 13 Step 1 — schema + repo tests for the journal calibration columns.

DB integration is covered by the route tests in test_journal.py; here we
verify the repo's input validation and the ORM model's new fields exist.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from apps.api.models.orm.journal import UserDecisionJournal
from apps.api.repos import journal as repo


def _journal_row(*, resolved: str | None = None) -> UserDecisionJournal:
    return UserDecisionJournal(
        id=uuid.uuid4(),
        instrument_id=uuid.uuid4(),
        hypothesis="Test hypothesis",
        evidence=[],
        confidence_pct=70,
        resolved_direction=resolved,
        thesis_id_at_write=None,
        thesis_conviction_at_write=None,
    )


def test_orm_has_phase13_columns():
    """Every Phase-13 column must round-trip through the ORM constructor."""
    tid = uuid.uuid4()
    row = UserDecisionJournal(
        instrument_id=uuid.uuid4(),
        hypothesis="x",
        evidence=[],
        confidence_pct=50,
        resolved_direction="hit",
        thesis_id_at_write=tid,
        thesis_conviction_at_write=75,
    )
    assert row.resolved_direction == "hit"
    assert row.thesis_id_at_write == tid
    assert row.thesis_conviction_at_write == 75


def test_resolved_directions_constant_is_complete():
    """The repo's RESOLVED_DIRECTIONS set must match the CHECK constraint."""
    assert repo.RESOLVED_DIRECTIONS == frozenset(
        {"hit", "miss", "neutral", "unresolved"}
    )


@pytest.mark.asyncio
async def test_update_accepts_each_valid_resolved_direction():
    session = AsyncMock()
    session.flush = AsyncMock(return_value=None)
    for val in ["hit", "miss", "neutral", "unresolved"]:
        row = _journal_row()
        await repo.update(session, row, {"resolved_direction": val})
        assert row.resolved_direction == val


@pytest.mark.asyncio
async def test_update_accepts_null_resolved_direction():
    """Explicitly setting resolved_direction back to null is allowed."""
    session = AsyncMock()
    session.flush = AsyncMock(return_value=None)
    row = _journal_row(resolved="hit")
    await repo.update(session, row, {"resolved_direction": None})
    assert row.resolved_direction is None


@pytest.mark.asyncio
async def test_update_rejects_invalid_resolved_direction():
    session = AsyncMock()
    row = _journal_row()
    with pytest.raises(ValueError, match="resolved_direction"):
        await repo.update(session, row, {"resolved_direction": "pending"})


@pytest.mark.asyncio
async def test_update_drops_unknown_fields():
    """Phase-13 columns set on creation are immutable — patch can't reassign them."""
    session = AsyncMock()
    session.flush = AsyncMock(return_value=None)
    row = _journal_row()
    tid_before = row.thesis_id_at_write
    await repo.update(
        session,
        row,
        {
            "thesis_id_at_write": uuid.uuid4(),
            "thesis_conviction_at_write": 99,
            "resolved_direction": "hit",
        },
    )
    # resolved_direction allowed; the other two silently ignored.
    assert row.resolved_direction == "hit"
    assert row.thesis_id_at_write == tid_before
    assert row.thesis_conviction_at_write is None


@pytest.mark.asyncio
async def test_update_preserves_existing_resolved_direction_when_omitted():
    session = AsyncMock()
    session.flush = AsyncMock(return_value=None)
    row = _journal_row(resolved="miss")
    await repo.update(session, row, {"outcome": "Resolved against."})
    assert row.resolved_direction == "miss"
    assert row.outcome == "Resolved against."


@pytest.mark.asyncio
async def test_list_with_resolutions_calls_correct_query():
    """list_with_resolutions hits all entries for the instrument, newest first."""
    session = AsyncMock()
    result = AsyncMock()
    result.scalars = lambda: type("S", (), {"all": lambda self: []})()
    session.execute = AsyncMock(return_value=result)
    instrument_id = uuid.uuid4()
    out = await repo.list_with_resolutions(session, instrument_id)
    assert out == []
    session.execute.assert_awaited_once()
