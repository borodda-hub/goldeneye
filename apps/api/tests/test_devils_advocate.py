"""Phase 6 — Devil's Advocate adversarial thesis engine.

Mirrors the critique test surface: prompt builder, JSON parser, async function +
envelope, routing escalation, and the POST /v1/thesis/{id}/devils-advocate route.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.api.models.orm.theses import Thesis
from apps.api.services import llm_routing
from apps.api.services.llm_explainer import (
    _parse_devils_advocate_json,
    devils_advocate,
)
from apps.api.services.llm_prompts import devils_advocate_messages
from apps.api.src.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _make_thesis(*, conviction: int = 70) -> Thesis:
    t = Thesis(
        id=uuid.uuid4(),
        instrument_code="NG",
        statement="Cold snap sustains storage draws into late March.",
        supporting_evidence=[{"factor": "weather", "weight": 0.6, "note": "NE cold"}],
        contradicting_evidence=[{"factor": "production_up", "weight": 0.3, "note": ""}],
        missing_data=["NWS 6-10 day"],
        conviction_pct=conviction,
        active=True,
    )
    t.created_at = datetime(2026, 5, 12, 12, 0, 0)
    t.updated_at = datetime(2026, 5, 12, 12, 0, 0)
    return t


def test_messages_frame_the_opposite_side():
    prompt = devils_advocate_messages(
        {"statement": "NG goes up", "conviction_pct": 80}
    )
    assert len(prompt.system_blocks) == 2
    block = prompt.system_blocks[1]["text"]
    assert "devils_advocate" in block
    assert "counter_thesis" in block
    assert "premortem" in block
    assert "invalidation_signals" in block
    assert "NG goes up" in prompt.user_messages[0]["content"]


def test_parse_happy_and_caps():
    out = _parse_devils_advocate_json(
        '{"counter_thesis": "deficit priced in", '
        '"premortem": ["a","b","c","d"], '
        '"invalidation_signals": ["s1","s2","s3","s4","s5"]}'
    )
    assert out["counter_thesis"] == "deficit priced in"
    assert len(out["premortem"]) == 3  # capped
    assert len(out["invalidation_signals"]) == 4  # capped


def test_parse_strips_fence_and_degrades():
    fenced = _parse_devils_advocate_json('```json\n{"counter_thesis": "x"}\n```')
    assert fenced["counter_thesis"] == "x"
    assert fenced["premortem"] == []
    bad = _parse_devils_advocate_json("not json {{{")
    assert bad == {"counter_thesis": "", "premortem": [], "invalidation_signals": []}


async def test_devils_advocate_returns_parsed_and_envelope():
    fake = (
        '{"counter_thesis": "already in the curve", '
        '"premortem": ["production rebounds"], '
        '"invalidation_signals": ["smaller EIA print Thu"]}'
    )
    with patch(
        "apps.api.services.llm_explainer._call_with_safety_check",
        new=AsyncMock(return_value=fake),
    ):
        parsed, envelope = await devils_advocate({"statement": "x", "conviction_pct": 65})
    assert parsed["counter_thesis"] == "already in the curve"
    assert parsed["premortem"] == ["production rebounds"]
    assert parsed["invalidation_signals"] == ["smaller EIA print Thu"]
    assert envelope.confidence == "medium"
    assert envelope.disclaimer


def test_routing_high_conviction_escalates_to_premium():
    from apps.api.src.settings import settings

    assert (
        llm_routing.select_model("devils_advocate", {"conviction_pct": 80})
        == settings.llm_model_premium
    )
    assert (
        llm_routing.select_model("devils_advocate", {"conviction_pct": 50})
        == settings.llm_model_smart
    )


def test_endpoint_404_when_missing(client: TestClient):
    with patch(
        "apps.api.routers.thesis.theses_repo.get_by_id",
        new=AsyncMock(return_value=None),
    ):
        resp = client.post(f"/v1/thesis/{uuid.uuid4()}/devils-advocate")
    assert resp.status_code == 404


def test_endpoint_happy_path(client: TestClient):
    thesis = _make_thesis()
    from apps.api.services.safety import wrap_with_uncertainty

    envelope = wrap_with_uncertainty(
        {}, confidence="medium", caveats=["c"], as_of=datetime.utcnow()
    )
    review = (
        {
            "counter_thesis": "deficit priced in",
            "premortem": ["production rebounds"],
            "invalidation_signals": ["smaller EIA print Thu"],
        },
        envelope,
    )
    with patch(
        "apps.api.routers.thesis.theses_repo.get_by_id",
        new=AsyncMock(return_value=thesis),
    ), patch(
        "apps.api.routers.thesis.llm_devils_advocate",
        new=AsyncMock(return_value=review),
    ):
        resp = client.post(f"/v1/thesis/{thesis.id}/devils-advocate")
    assert resp.status_code == 200
    body = resp.json()
    assert body["counter_thesis"] == "deficit priced in"
    assert body["premortem"] == ["production rebounds"]
    assert body["invalidation_signals"] == ["smaller EIA print Thu"]
    assert "Goldeneye" in body["safety"]["disclaimer"]
