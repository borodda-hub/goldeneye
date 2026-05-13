"""Phase 12 Step 3 — LLM critique service + endpoint tests.

Covers:
- critique_thesis_messages prompt structure (system blocks, instructions, JSON
  schema hint)
- _parse_critique_json — happy JSON, JSON inside code fences, malformed input
- critique_thesis() async — mocked LLM, returns parsed dict + envelope
- POST /v1/thesis/{id}/critique — 404 + happy path
- llm_routing escalation to premium for high-conviction theses
"""
from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.api.models.orm.theses import Thesis
from apps.api.services import llm_routing
from apps.api.services.llm_explainer import _parse_critique_json, critique_thesis
from apps.api.services.llm_prompts import critique_thesis_messages
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


# ── Prompt builder ────────────────────────────────────────────────────────


def test_messages_contain_persona_and_task_blocks():
    thesis = {
        "statement": "Test statement",
        "supporting_evidence": [{"factor": "weather", "weight": 0.5, "note": ""}],
        "contradicting_evidence": [],
        "missing_data": ["EIA Weekly Storage"],
        "conviction_pct": 70,
    }
    prompt = critique_thesis_messages(thesis)
    assert len(prompt.system_blocks) == 2
    assert prompt.system_blocks[0]["cache_control"] == {"type": "ephemeral"}
    # Task instructions name the task explicitly.
    assert "critique_thesis" in prompt.system_blocks[1]["text"]
    # JSON schema appears in the task block.
    assert "missed_risks" in prompt.system_blocks[1]["text"]
    assert "blind_spots" in prompt.system_blocks[1]["text"]
    assert "questions" in prompt.system_blocks[1]["text"]
    # User content carries the thesis statement.
    user = prompt.user_messages[0]["content"]
    assert "Test statement" in user
    assert "70%" in user


def test_messages_handle_missing_fields():
    """If a thesis comes in with missing keys, the builder must not crash."""
    prompt = critique_thesis_messages({"statement": "Bare statement"})
    user = prompt.user_messages[0]["content"]
    assert "Bare statement" in user
    assert "none" in user.lower()  # supporting/contradicting/missing → "none"


def test_messages_cap_factors_at_five():
    thesis = {
        "statement": "Many factors",
        "supporting_evidence": [{"factor": f"f{i}", "weight": 0.1} for i in range(10)],
        "contradicting_evidence": [],
        "missing_data": [],
        "conviction_pct": 50,
    }
    prompt = critique_thesis_messages(thesis)
    user = prompt.user_messages[0]["content"]
    # First 5 included, latter 5 not.
    assert "f0" in user
    assert "f4" in user
    assert "f9" not in user


# ── JSON parser ───────────────────────────────────────────────────────────


def test_parse_json_happy_path():
    text = (
        '{"missed_risks": ["a", "b"], "blind_spots": ["c"], '
        '"questions": ["d", "e"]}'
    )
    result = _parse_critique_json(text)
    assert result == {
        "missed_risks": ["a", "b"],
        "blind_spots": ["c"],
        "questions": ["d", "e"],
    }


def test_parse_json_strips_code_fence():
    text = (
        "```json\n"
        '{"missed_risks": ["x"], "blind_spots": [], "questions": ["y"]}\n'
        "```"
    )
    result = _parse_critique_json(text)
    assert result["missed_risks"] == ["x"]
    assert result["questions"] == ["y"]


def test_parse_json_caps_field_lengths():
    text = (
        '{"missed_risks": ' + str([f"r{i}" for i in range(10)]).replace("'", '"') + ", "
        '"blind_spots": ' + str([f"b{i}" for i in range(10)]).replace("'", '"') + ", "
        '"questions": ' + str([f"q{i}" for i in range(10)]).replace("'", '"') + "}"
    )
    result = _parse_critique_json(text)
    assert len(result["missed_risks"]) == 5
    assert len(result["blind_spots"]) == 4
    assert len(result["questions"]) == 4


def test_parse_malformed_json_degrades_gracefully():
    result = _parse_critique_json("not actually json {{{")
    assert result == {"missed_risks": [], "blind_spots": [], "questions": []}


def test_parse_missing_keys_returns_empty_lists():
    result = _parse_critique_json('{"missed_risks": ["only this"]}')
    assert result["missed_risks"] == ["only this"]
    assert result["blind_spots"] == []
    assert result["questions"] == []


# ── critique_thesis async function ────────────────────────────────────────


@pytest.mark.asyncio
async def test_critique_thesis_returns_parsed_and_envelope():
    fake_json = (
        '{"missed_risks": ["LNG outage tail-risk"], '
        '"blind_spots": ["assumes weather skill > day 7"], '
        '"questions": ["What invalidates this in 7 days?"]}'
    )
    thesis_dict = {
        "statement": "Cold snap sustains draws.",
        "supporting_evidence": [],
        "contradicting_evidence": [],
        "missing_data": [],
        "conviction_pct": 65,
    }
    with patch(
        "apps.api.services.llm_explainer._call_with_safety_check",
        new=AsyncMock(return_value=fake_json),
    ):
        parsed, envelope = await critique_thesis(thesis_dict)

    assert parsed["missed_risks"] == ["LNG outage tail-risk"]
    assert parsed["blind_spots"] == ["assumes weather skill > day 7"]
    assert parsed["questions"] == ["What invalidates this in 7 days?"]
    assert envelope.confidence == "medium"
    # Disclaimer present, caveats present, forbidden phrases absent — covered by
    # wrap_with_uncertainty; this verifies the path was taken.
    assert envelope.disclaimer
    assert len(envelope.caveats) >= 2


# ── llm_routing ──────────────────────────────────────────────────────────


def test_routing_critique_low_conviction_uses_smart():
    model = llm_routing.select_model("critique_thesis", {"conviction_pct": 50})
    # Smart tier (Sonnet by default).
    from apps.api.src.settings import settings

    assert model == settings.llm_model_smart


def test_routing_critique_high_conviction_escalates_to_premium():
    model = llm_routing.select_model("critique_thesis", {"conviction_pct": 90})
    from apps.api.src.settings import settings

    assert model == settings.llm_model_premium


def test_routing_critique_boundary_at_80():
    """Threshold is >= 80, so exactly 80 should escalate."""
    model = llm_routing.select_model("critique_thesis", {"conviction_pct": 80})
    from apps.api.src.settings import settings

    assert model == settings.llm_model_premium


# ── Endpoint POST /v1/thesis/{id}/critique ────────────────────────────────


def test_critique_endpoint_404_when_missing(client: TestClient):
    with patch(
        "apps.api.routers.thesis.theses_repo.get_by_id",
        new=AsyncMock(return_value=None),
    ):
        resp = client.post(f"/v1/thesis/{uuid.uuid4()}/critique")
    assert resp.status_code == 404


def test_critique_endpoint_happy_path(client: TestClient):
    thesis = _make_thesis()
    from apps.api.services.safety import wrap_with_uncertainty

    envelope = wrap_with_uncertainty(
        {},
        confidence="medium",
        caveats=["Test caveat."],
        as_of=datetime.utcnow(),
    )
    payload = (
        {"missed_risks": ["risk A"], "blind_spots": ["bs A"], "questions": ["q A"]},
        envelope,
    )
    with patch(
        "apps.api.routers.thesis.theses_repo.get_by_id",
        new=AsyncMock(return_value=thesis),
    ), patch(
        "apps.api.routers.thesis.llm_critique_thesis",
        new=AsyncMock(return_value=payload),
    ):
        resp = client.post(f"/v1/thesis/{thesis.id}/critique")
    assert resp.status_code == 200
    body = resp.json()
    assert body["missed_risks"] == ["risk A"]
    assert body["blind_spots"] == ["bs A"]
    assert body["questions"] == ["q A"]
    assert body["safety"]["confidence"] == "medium"
    # The disclaimer is the Goldeneye one we set in Phase 11.
    assert "Goldeneye" in body["safety"]["disclaimer"]
