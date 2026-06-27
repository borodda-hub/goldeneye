"""Phase 13 Step 4 — journal endpoint changes.

Covers:
- POST /v1/journal auto-fills thesis_id_at_write + thesis_conviction_at_write
  when an active thesis exists for the instrument
- POST /v1/journal leaves those columns NULL when no active thesis
- PATCH /v1/journal/{id} accepts resolved_direction
- PATCH 400's on invalid resolved_direction (repo ValueError mapping)
- PATCH preserves resolved_direction when omitted (exclude_unset semantics)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.api.models.orm.journal import UserDecisionJournal
from apps.api.models.orm.theses import Thesis
from apps.api.src.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _stub_ledger():
    """B4 hooks the immutable-ledger append + system-context capture into the
    journal create/patch paths. These are mocked endpoint tests with no DB, so
    stub the two ledger calls (their behavior is covered by
    tests/test_ledger_service.py and the gated tests/db/test_ledger_e2e.py)."""
    with patch(
        "apps.api.routers.journal.ledger_repo.append_event",
        new=AsyncMock(),
    ), patch(
        "apps.api.routers.journal.ledger_svc.capture_system_context",
        new=AsyncMock(return_value={"captured": False, "reason": "stubbed in test"}),
    ):
        yield


def _fake_instrument() -> Any:
    return type("I", (), {"id": uuid.uuid4()})()


def _fake_thesis(*, conviction: int = 72) -> Thesis:
    t = Thesis(
        id=uuid.uuid4(),
        instrument_code="NG",
        statement="Cold snap sustains storage draws.",
        supporting_evidence=[],
        contradicting_evidence=[],
        missing_data=[],
        conviction_pct=conviction,
        active=True,
    )
    t.created_at = datetime(2026, 5, 12, 12, 0, 0)
    t.updated_at = datetime(2026, 5, 12, 12, 0, 0)
    return t


def _fake_journal_entry(
    *,
    instrument_id: uuid.UUID,
    thesis_id: uuid.UUID | None = None,
    thesis_conviction: int | None = None,
    resolved: str | None = None,
) -> UserDecisionJournal:
    e = UserDecisionJournal(
        id=uuid.uuid4(),
        instrument_id=instrument_id,
        hypothesis="Test hypothesis",
        evidence=[],
        confidence_pct=70,
        thesis_id_at_write=thesis_id,
        thesis_conviction_at_write=thesis_conviction,
        resolved_direction=resolved,
    )
    e.created_at = datetime(2026, 5, 12, 13, 0, 0)
    return e


# ── POST happy path: thesis snapshot wired ────────────────────────────────


def test_post_snapshots_active_thesis(client: TestClient):
    instrument = _fake_instrument()
    thesis = _fake_thesis(conviction=72)

    captured: dict = {}

    async def fake_create(session, instrument_id, data):
        captured["data"] = data
        return _fake_journal_entry(
            instrument_id=instrument_id,
            thesis_id=data.get("thesis_id_at_write"),
            thesis_conviction=data.get("thesis_conviction_at_write"),
        )

    with patch(
        "apps.api.routers.journal.instr_repo.get_by_symbol",
        new=AsyncMock(return_value=instrument),
    ), patch(
        "apps.api.routers.journal.theses_repo.get_active",
        new=AsyncMock(return_value=thesis),
    ), patch(
        "apps.api.routers.journal.journal_repo.create",
        new=AsyncMock(side_effect=fake_create),
    ), patch(
        "apps.api.routers.journal.review_journal_entry",
        new=AsyncMock(side_effect=Exception("skip LLM in test")),
    ):
        resp = client.post(
            "/v1/journal",
            json={
                "hypothesis": "Test hypothesis",
                "evidence": [],
                "confidence_pct": 70,
            },
        )
    assert resp.status_code == 200
    assert captured["data"]["thesis_id_at_write"] == thesis.id
    assert captured["data"]["thesis_conviction_at_write"] == 72
    body = resp.json()
    assert body["thesis_id_at_write"] == str(thesis.id)
    assert body["thesis_conviction_at_write"] == 72


def test_post_skips_snapshot_when_no_active_thesis(client: TestClient):
    instrument = _fake_instrument()
    captured: dict = {}

    async def fake_create(session, instrument_id, data):
        captured["data"] = data
        return _fake_journal_entry(instrument_id=instrument_id)

    with patch(
        "apps.api.routers.journal.instr_repo.get_by_symbol",
        new=AsyncMock(return_value=instrument),
    ), patch(
        "apps.api.routers.journal.theses_repo.get_active",
        new=AsyncMock(return_value=None),
    ), patch(
        "apps.api.routers.journal.journal_repo.create",
        new=AsyncMock(side_effect=fake_create),
    ), patch(
        "apps.api.routers.journal.review_journal_entry",
        new=AsyncMock(side_effect=Exception("skip LLM")),
    ):
        resp = client.post(
            "/v1/journal",
            json={
                "hypothesis": "Test hypothesis",
                "evidence": [],
                "confidence_pct": 60,
            },
        )
    assert resp.status_code == 200
    assert "thesis_id_at_write" not in captured["data"]
    assert "thesis_conviction_at_write" not in captured["data"]
    body = resp.json()
    assert body["thesis_id_at_write"] is None
    assert body["thesis_conviction_at_write"] is None


# ── PATCH: resolved_direction acceptance ──────────────────────────────────


def test_patch_accepts_resolved_direction(client: TestClient):
    instrument_id = uuid.uuid4()
    existing = _fake_journal_entry(instrument_id=instrument_id)

    async def fake_update(session, entry, patch):
        for k, v in patch.items():
            setattr(entry, k, v)
        return entry

    with patch(
        "apps.api.routers.journal.journal_repo.get_by_id",
        new=AsyncMock(return_value=existing),
    ), patch(
        "apps.api.routers.journal.journal_repo.update",
        new=AsyncMock(side_effect=fake_update),
    ):
        resp = client.patch(
            f"/v1/journal/{existing.id}",
            json={"resolved_direction": "hit"},
        )
    assert resp.status_code == 200
    assert resp.json()["resolved_direction"] == "hit"


def test_patch_rejects_invalid_resolved_direction(client: TestClient):
    """Pydantic Literal rejects unknown enum values upfront → 422."""
    instrument_id = uuid.uuid4()
    existing = _fake_journal_entry(instrument_id=instrument_id)
    with patch(
        "apps.api.routers.journal.journal_repo.get_by_id",
        new=AsyncMock(return_value=existing),
    ):
        resp = client.patch(
            f"/v1/journal/{existing.id}",
            json={"resolved_direction": "pending"},
        )
    assert resp.status_code == 422


def test_patch_clears_resolved_direction_when_explicitly_null(client: TestClient):
    instrument_id = uuid.uuid4()
    existing = _fake_journal_entry(
        instrument_id=instrument_id, resolved="hit"
    )

    async def fake_update(session, entry, patch):
        for k, v in patch.items():
            setattr(entry, k, v)
        return entry

    with patch(
        "apps.api.routers.journal.journal_repo.get_by_id",
        new=AsyncMock(return_value=existing),
    ), patch(
        "apps.api.routers.journal.journal_repo.update",
        new=AsyncMock(side_effect=fake_update),
    ):
        resp = client.patch(
            f"/v1/journal/{existing.id}",
            json={"resolved_direction": None},
        )
    assert resp.status_code == 200
    assert resp.json()["resolved_direction"] is None


def test_patch_preserves_resolved_direction_when_omitted(client: TestClient):
    """If the client sends only `outcome`, the existing resolved_direction
    stays untouched (exclude_unset behavior)."""
    instrument_id = uuid.uuid4()
    existing = _fake_journal_entry(
        instrument_id=instrument_id, resolved="hit"
    )
    captured: dict = {}

    async def fake_update(session, entry, patch_data):
        captured["patch"] = patch_data
        for k, v in patch_data.items():
            setattr(entry, k, v)
        return entry

    with patch(
        "apps.api.routers.journal.journal_repo.get_by_id",
        new=AsyncMock(return_value=existing),
    ), patch(
        "apps.api.routers.journal.journal_repo.update",
        new=AsyncMock(side_effect=fake_update),
    ):
        resp = client.patch(
            f"/v1/journal/{existing.id}",
            json={"outcome": "Resolved in favor."},
        )
    assert resp.status_code == 200
    # resolved_direction key should NOT appear in the patch.
    assert "resolved_direction" not in captured["patch"]
    assert resp.json()["resolved_direction"] == "hit"
