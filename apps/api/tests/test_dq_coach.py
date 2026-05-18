"""Phase 13.8 — DQ coach service + endpoint tests."""
from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.api.models.orm.journal import UserDecisionJournal
from apps.api.services import dq_coach
from apps.api.services.calibration import (
    CalibrationBucket,
    CalibrationResult,
)
from apps.api.services.llm_prompts import coach_dq_messages
from apps.api.src.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _bucket(
    *,
    label: str = "60-80",
    claimed: float | None = 70.0,
    total: int = 4,
    resolved: int = 3,
    hits: int = 2,
    hit_rate: float | None = 2 / 3,
) -> CalibrationBucket:
    return CalibrationBucket(
        label=label,
        lower_pct=60,
        upper_pct=80,
        claimed_mean=claimed,
        total_count=total,
        resolved_count=resolved,
        hit_count=hits,
        hit_rate=hit_rate,
    )


def _calibration(buckets: list[CalibrationBucket]) -> CalibrationResult:
    return CalibrationResult(
        instrument_code="NG",
        buckets=buckets,
        total_entries=sum(b.total_count for b in buckets),
        resolved_entries=sum(b.resolved_count for b in buckets),
        unresolved_entries=0,
        summary=None,
    )


def _entry(
    *,
    hypothesis: str = "Cold snap sustains storage draws.",
    conviction: int = 70,
    resolved: str | None = "hit",
) -> UserDecisionJournal:
    return UserDecisionJournal(
        id=uuid.uuid4(),
        instrument_id=uuid.uuid4(),
        hypothesis=hypothesis,
        evidence=[],
        confidence_pct=conviction,
        thesis_conviction_at_write=conviction,
        resolved_direction=resolved,
    )


# ── Prompt builder ────────────────────────────────────────────────────────


def test_messages_include_bucket_summary_and_entry_excerpts():
    cal = {
        "buckets": [
            {
                "label": "60-80",
                "claimed_mean": 70.0,
                "total_count": 4,
                "resolved_count": 3,
                "hit_count": 2,
                "hit_rate": 2 / 3,
            }
        ]
    }
    entries = [
        {
            "hypothesis": "Cold snap demand boost",
            "thesis_conviction_at_write": 70,
            "confidence_pct": 70,
            "resolved_direction": "hit",
        },
        {
            "hypothesis": "LNG outage will be slow to repair",
            "thesis_conviction_at_write": 60,
            "confidence_pct": 60,
            "resolved_direction": "miss",
        },
    ]
    prompt = coach_dq_messages(cal, entries)
    user = prompt.user_messages[0]["content"]
    assert "Bucket 60-80%" in user
    assert "70%" in user  # claimed_mean
    assert "hit_rate=67%" in user
    assert "Cold snap" in user
    assert "[hit, conviction=70%]" in user
    assert "[miss, conviction=60%]" in user


def test_messages_cap_entries_at_thirty():
    cal = {"buckets": []}
    entries = [
        {
            "hypothesis": f"Entry {i}",
            "thesis_conviction_at_write": 50,
            "confidence_pct": 50,
            "resolved_direction": "hit",
        }
        for i in range(50)
    ]
    prompt = coach_dq_messages(cal, entries)
    user = prompt.user_messages[0]["content"]
    assert "showing 30 of 50" in user
    assert "Entry 0" in user
    assert "Entry 29" in user
    assert "Entry 30" not in user


# ── JSON parser ───────────────────────────────────────────────────────────


def test_parse_json_happy_path():
    raw = (
        '{"buckets": ['
        '{"label": "60-80", "effective_patterns": ["A", "B"], '
        '"failure_patterns": ["C"], "recommendation": "Do X."}'
        '], "overall": {"synthesis": "S", "top_recommendation": "T"}}'
    )
    result = dq_coach._parse_coaching_json(raw)
    assert len(result["buckets"]) == 1
    b = result["buckets"][0]
    assert b["label"] == "60-80"
    assert b["effective_patterns"] == ["A", "B"]
    assert b["failure_patterns"] == ["C"]
    assert b["recommendation"] == "Do X."
    assert result["overall"]["synthesis"] == "S"


def test_parse_json_strips_code_fence():
    raw = (
        "```json\n"
        '{"buckets": [], "overall": {"synthesis": "X", "top_recommendation": "Y"}}\n'
        "```"
    )
    result = dq_coach._parse_coaching_json(raw)
    assert result["overall"]["synthesis"] == "X"


def test_parse_json_caps_patterns_at_three():
    raw = (
        '{"buckets": [{"label": "x", '
        '"effective_patterns": ["a","b","c","d","e","f"], '
        '"failure_patterns": ["g","h","i","j"], "recommendation": "r"}], '
        '"overall": {"synthesis": "", "top_recommendation": ""}}'
    )
    result = dq_coach._parse_coaching_json(raw)
    assert len(result["buckets"][0]["effective_patterns"]) == 3
    assert len(result["buckets"][0]["failure_patterns"]) == 3


def test_parse_malformed_returns_empty():
    result = dq_coach._parse_coaching_json("not json {{")
    assert result == {
        "buckets": [],
        "overall": {"synthesis": "", "top_recommendation": ""},
    }


def test_parse_missing_overall_returns_empty_overall():
    raw = '{"buckets": []}'
    result = dq_coach._parse_coaching_json(raw)
    assert result["overall"] == {"synthesis": "", "top_recommendation": ""}


# ── coach_decision_quality service ────────────────────────────────────────


@pytest.mark.asyncio
async def test_service_skips_llm_when_zero_resolved():
    """No resolved entries → return empty coaching + low-confidence envelope."""
    cal = _calibration([_bucket(resolved=0, hits=0, hit_rate=None)])
    entries = [_entry(resolved=None), _entry(resolved="unresolved")]
    with patch.object(
        dq_coach, "compute_calibration", new=AsyncMock(return_value=cal)
    ), patch.object(
        dq_coach.journal_repo,
        "list_with_resolutions",
        new=AsyncMock(return_value=entries),
    ), patch.object(
        dq_coach,
        "_call_with_safety_check",
        new=AsyncMock(side_effect=AssertionError("LLM should not be called")),
    ):
        result, envelope = await dq_coach.coach_decision_quality(
            session=None,  # type: ignore[arg-type]
            instrument_id=uuid.uuid4(),
            instrument_code="NG",
        )
    assert result["buckets"] == []
    assert envelope.confidence == "low"
    assert any("at least 3" in c for c in envelope.caveats)


@pytest.mark.asyncio
async def test_service_calls_llm_and_parses_response():
    cal = _calibration([_bucket()])
    entries = [
        _entry(resolved="hit", hypothesis="A"),
        _entry(resolved="hit", hypothesis="B"),
        _entry(resolved="miss", hypothesis="C"),
    ]
    fake_json = (
        '{"buckets": [{"label": "60-80", '
        '"effective_patterns": ["weather"], '
        '"failure_patterns": ["overweighted LNG"], '
        '"recommendation": "Score weather skill before sizing."}], '
        '"overall": {"synthesis": "Good at storage reads.", '
        '"top_recommendation": "Tighten invalidation criteria."}}'
    )
    with patch.object(
        dq_coach, "compute_calibration", new=AsyncMock(return_value=cal)
    ), patch.object(
        dq_coach.journal_repo,
        "list_with_resolutions",
        new=AsyncMock(return_value=entries),
    ), patch.object(
        dq_coach,
        "_call_with_safety_check",
        new=AsyncMock(return_value=fake_json),
    ):
        result, envelope = await dq_coach.coach_decision_quality(
            session=None,  # type: ignore[arg-type]
            instrument_id=uuid.uuid4(),
            instrument_code="NG",
        )
    assert result["buckets"][0]["effective_patterns"] == ["weather"]
    assert (
        result["overall"]["top_recommendation"]
        == "Tighten invalidation criteria."
    )
    assert envelope.confidence in ("low", "medium")
    assert envelope.disclaimer  # Goldeneye disclaimer present


# ── Endpoint ──────────────────────────────────────────────────────────────


def test_coaching_endpoint_404_when_symbol_unknown(client: TestClient):
    with patch(
        "apps.api.routers.calibration.instr_repo.get_by_symbol",
        new=AsyncMock(return_value=None),
    ):
        resp = client.get("/v1/calibration/coaching?instrument_code=ZZZ")
    assert resp.status_code == 404


def test_coaching_endpoint_happy_path(client: TestClient):
    instrument = type("I", (), {"id": uuid.uuid4()})()
    from apps.api.services.safety import wrap_with_uncertainty

    envelope = wrap_with_uncertainty(
        {},
        confidence="medium",
        caveats=["Test caveat."],
        as_of=datetime.utcnow(),
    )
    payload = (
        {
            "buckets": [
                {
                    "label": "60-80",
                    "effective_patterns": ["P1"],
                    "failure_patterns": ["F1"],
                    "recommendation": "R1",
                }
            ],
            "overall": {"synthesis": "S", "top_recommendation": "T"},
        },
        envelope,
    )
    with patch(
        "apps.api.routers.calibration.instr_repo.get_by_symbol",
        new=AsyncMock(return_value=instrument),
    ), patch(
        "apps.api.routers.calibration.coach_decision_quality",
        new=AsyncMock(return_value=payload),
    ):
        resp = client.get("/v1/calibration/coaching")
    assert resp.status_code == 200
    body = resp.json()
    assert body["instrument_code"] == "NG"
    assert body["buckets"][0]["effective_patterns"] == ["P1"]
    assert body["overall"]["top_recommendation"] == "T"
    assert "Goldeneye" in body["safety"]["disclaimer"]
