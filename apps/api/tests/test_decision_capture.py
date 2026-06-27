"""Phase 2 — structured ex-ante decision capture (LLM-extract + confirm).

Covers the prediction parser/clamps, the fake-mode extractor, the
/extract-prediction endpoint, and that POST /v1/journal persists the confirmed
claim + anchor price.
"""
from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.api.services.llm_explainer import _parse_prediction_json, extract_prediction
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


def _fake_contract(code: str = "NGM26") -> Any:
    return type("C", (), {"id": uuid.uuid4(), "contract_code": code})()


# ── parser: defaults + clamps ─────────────────────────────────────────────


def test_parse_prediction_happy():
    out = _parse_prediction_json(
        '{"direction":"bearish","horizon_days":7,"threshold_pct":1.5,"rationale":"x"}'
    )
    assert out == {
        "direction": "bearish",
        "horizon_days": 7,
        "threshold_pct": 1.5,
        "rationale": "x",
    }


def test_parse_prediction_clamps_and_defaults():
    out = _parse_prediction_json(
        '{"direction":"sideways","horizon_days":900,"threshold_pct":999}'
    )
    assert out["direction"] == "neutral"  # unknown → neutral
    assert out["horizon_days"] == 90  # clamped to max
    assert out["threshold_pct"] == 50.0  # clamped to max


def test_parse_prediction_strips_code_fence_and_survives_garbage():
    fenced = _parse_prediction_json('```json\n{"direction":"bullish"}\n```')
    assert fenced["direction"] == "bullish"
    assert fenced["horizon_days"] == 14  # default
    garbage = _parse_prediction_json("not json at all")
    assert garbage == {
        "direction": "neutral",
        "horizon_days": 14,
        "threshold_pct": 2.0,
        "rationale": "",
    }


async def test_extract_prediction_fake_mode_returns_canned_shape():
    out = await extract_prediction("Cold snap sustains storage draws.", "NG", 3.2)
    assert out["direction"] == "bullish"
    assert out["horizon_days"] == 14
    assert out["threshold_pct"] == 2.0
    assert isinstance(out["rationale"], str)


# ── /extract-prediction endpoint ──────────────────────────────────────────


def test_extract_prediction_endpoint(client: TestClient):
    instrument = _fake_instrument()
    with patch(
        "apps.api.routers.journal.instr_repo.get_by_symbol",
        new=AsyncMock(return_value=instrument),
    ), patch(
        "apps.api.routers.journal.contract_repo.get_front_month",
        new=AsyncMock(return_value=_fake_contract()),
    ), patch(
        "apps.api.routers.journal.get_latest_closes",
        new=AsyncMock(return_value=[3.2]),
    ):
        resp = client.post(
            "/v1/journal/extract-prediction",
            json={"instrument": "NG", "hypothesis": "Storage deficit should lift NG."},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["anchor_price"] == 3.2
    assert body["prediction"]["direction"] == "bullish"
    assert body["prediction"]["horizon_days"] == 14


def test_extract_prediction_endpoint_unknown_instrument(client: TestClient):
    with patch(
        "apps.api.routers.journal.instr_repo.get_by_symbol",
        new=AsyncMock(return_value=None),
    ):
        resp = client.post(
            "/v1/journal/extract-prediction",
            json={"instrument": "ZZ", "hypothesis": "x"},
        )
    assert resp.status_code == 404


# ── create persists the confirmed claim + anchor ──────────────────────────


def test_create_persists_prediction_and_anchor(client: TestClient):
    instrument = _fake_instrument()
    captured: dict = {}

    async def fake_create(session, instrument_id, data):
        captured["data"] = data
        from datetime import datetime

        from apps.api.models.orm.journal import UserDecisionJournal

        e = UserDecisionJournal(
            id=uuid.uuid4(),
            instrument_id=instrument_id,
            hypothesis="h",
            evidence=[],
            confidence_pct=70,
            predicted_direction=data.get("predicted_direction"),
            horizon_days=data.get("horizon_days"),
            threshold_pct=data.get("threshold_pct"),
            anchor_price=data.get("anchor_price"),
        )
        e.created_at = datetime(2026, 6, 6, 12, 0, 0)
        return e

    with patch(
        "apps.api.routers.journal.instr_repo.get_by_symbol",
        new=AsyncMock(return_value=instrument),
    ), patch(
        "apps.api.routers.journal.theses_repo.get_active",
        new=AsyncMock(return_value=None),
    ), patch(
        "apps.api.routers.journal.contract_repo.get_front_month",
        new=AsyncMock(return_value=_fake_contract()),
    ), patch(
        "apps.api.routers.journal.get_latest_closes",
        new=AsyncMock(return_value=[3.25]),
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
                "hypothesis": "Storage deficit should lift NG.",
                "evidence": [],
                "confidence_pct": 70,
                "predicted_direction": "bullish",
                "horizon_days": 14,
                "threshold_pct": 2.0,
            },
        )
    assert resp.status_code == 200
    d = captured["data"]
    assert d["predicted_direction"] == "bullish"
    assert d["horizon_days"] == 14
    assert d["threshold_pct"] == 2.0
    assert d["anchor_price"] == 3.25  # captured from the front-month close
    body = resp.json()
    assert body["predicted_direction"] == "bullish"
    assert body["anchor_price"] == 3.25
