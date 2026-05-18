"""Phase 13 Step 2 — Signal Quality grading tests.

Covers each sub-score classifier, the grade-cutoff mapping, the full
compute_grade async path (with mocked DB), and the HTTP endpoint.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.api.services import signal_quality as sq
from apps.api.src.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ── Sub-score classifiers ─────────────────────────────────────────────────


def test_input_diversity_score_map():
    assert sq._score_input_diversity({"input_diversity": "high"}) == 30
    assert sq._score_input_diversity({"input_diversity": "medium"}) == 20
    assert sq._score_input_diversity({"input_diversity": "low"}) == 10
    # Unknown / missing → 0.
    assert sq._score_input_diversity({}) == 10  # default "low"
    assert sq._score_input_diversity({"input_diversity": "garbage"}) == 0


def test_model_agreement_score_perfect_consensus():
    score = sq._score_model_agreement(
        {"bullish": 4, "bearish": 0, "neutral": 0, "total": 4}
    )
    assert score == 25  # 25 × (4/4)


def test_model_agreement_score_split_vote():
    score = sq._score_model_agreement(
        {"bullish": 2, "bearish": 1, "neutral": 1, "total": 4}
    )
    # 25 × (2/4) = 12.5 → 12 under Python's banker's rounding (round-half-even).
    assert score == 12


def test_model_agreement_score_zero_total():
    assert sq._score_model_agreement({"total": 0}) == 0
    assert sq._score_model_agreement({}) == 0


def test_regime_stability_classification():
    assert sq._classify_regime_stability(["normal"] * 10) == "stable"
    assert sq._classify_regime_stability(["normal", "elevated"]) == "mixed"
    assert sq._classify_regime_stability(["normal", "elevated", "crisis"]) == "volatile"
    # None values are ignored.
    assert sq._classify_regime_stability([None, None, "normal"]) == "stable"
    # Empty input → 0 distinct → stable.
    assert sq._classify_regime_stability([]) == "stable"


def test_time_to_decision_buckets():
    assert sq._classify_time_to_decision(30) == (20, "≤60m")
    assert sq._classify_time_to_decision(60) == (20, "≤60m")
    assert sq._classify_time_to_decision(61) == (15, "≤4h")
    assert sq._classify_time_to_decision(240) == (15, "≤4h")
    assert sq._classify_time_to_decision(241) == (10, "≤24h")
    assert sq._classify_time_to_decision(1440) == (10, "≤24h")
    assert sq._classify_time_to_decision(1441) == (0, ">24h")
    assert sq._classify_time_to_decision(None) == (0, "no-data")


# ── Grade cutoffs ────────────────────────────────────────────────────────


def test_grade_for_each_band():
    assert sq._grade_for(100) == "A+"
    assert sq._grade_for(90) == "A+"
    assert sq._grade_for(89) == "A"
    assert sq._grade_for(80) == "A"
    assert sq._grade_for(79) == "B"
    assert sq._grade_for(70) == "B"
    assert sq._grade_for(69) == "C"
    assert sq._grade_for(60) == "C"
    assert sq._grade_for(59) == "D"
    assert sq._grade_for(0) == "D"


# ── compute_grade — full async path ───────────────────────────────────────


@pytest.mark.asyncio
async def test_compute_grade_perfect_score():
    """High diversity + 4/4 consensus + stable regime + fresh adapter
    runs should score 100 (A+)."""
    ensemble = {
        "agreement": {
            "input_diversity": "high",
            "bullish": 4,
            "bearish": 0,
            "neutral": 0,
            "total": 4,
        }
    }

    with patch.object(
        sq, "_vol_regimes_last_14d", new=AsyncMock(return_value=["normal"] * 10)
    ), patch.object(
        sq, "_minutes_since_latest_freshness_adapter", new=AsyncMock(return_value=30.0)
    ):
        result = await sq.compute_grade(
            session=None,  # type: ignore[arg-type]
            instrument_id=uuid.uuid4(),
            ensemble=ensemble,
            now=datetime(2026, 5, 12, 12, 0, 0),
        )
    assert result.total_score == 100
    assert result.grade == "A+"
    assert result.sub_scores == {
        "input_diversity": 30,
        "model_agreement": 25,
        "regime_stability": 25,
        "time_to_decision": 20,
    }


@pytest.mark.asyncio
async def test_compute_grade_low_score_d_grade():
    """All worst buckets → D grade."""
    ensemble = {
        "agreement": {
            "input_diversity": "low",
            "bullish": 1,
            "bearish": 1,
            "neutral": 2,
            "total": 4,
        }
    }
    with patch.object(
        sq,
        "_vol_regimes_last_14d",
        new=AsyncMock(return_value=["normal", "elevated", "crisis"]),
    ), patch.object(
        sq, "_minutes_since_latest_freshness_adapter", new=AsyncMock(return_value=None)
    ):
        result = await sq.compute_grade(
            session=None,  # type: ignore[arg-type]
            instrument_id=uuid.uuid4(),
            ensemble=ensemble,
            now=datetime(2026, 5, 12, 12, 0, 0),
        )
    # diversity=10 + agreement=round(25 × 2/4)=12 + regime=5 + freshness=0 → 27 D
    assert result.grade == "D"
    assert result.sub_scores["regime_stability"] == 5
    assert result.sub_scores["time_to_decision"] == 0


@pytest.mark.asyncio
async def test_compute_grade_detail_block_populated():
    ensemble = {
        "agreement": {
            "input_diversity": "medium",
            "bullish": 3,
            "bearish": 1,
            "neutral": 0,
            "total": 4,
        }
    }
    with patch.object(
        sq, "_vol_regimes_last_14d", new=AsyncMock(return_value=["normal", "elevated"])
    ), patch.object(
        sq, "_minutes_since_latest_freshness_adapter", new=AsyncMock(return_value=120.0)
    ):
        result = await sq.compute_grade(
            session=None,  # type: ignore[arg-type]
            instrument_id=uuid.uuid4(),
            ensemble=ensemble,
            now=datetime(2026, 5, 12, 12, 0, 0),
        )
    assert result.detail["input_diversity"] == "medium"
    assert result.detail["model_agreement_total"] == 4
    assert result.detail["model_agreement_max"] == 3
    assert result.detail["regime_stability"] == "mixed"
    assert result.detail["distinct_regimes_14d"] == 2
    assert result.detail["time_to_decision_bucket"] == "≤4h"
    assert result.detail["minutes_since_freshness_adapter"] == 120


# ── Endpoint ──────────────────────────────────────────────────────────────


def test_endpoint_404_when_symbol_unknown(client: TestClient):
    with patch(
        "apps.api.routers.signal_quality.instr_repo.get_by_symbol",
        new=AsyncMock(return_value=None),
    ):
        resp = client.get("/v1/signal-quality?symbol=ZZZ")
    assert resp.status_code == 404
    assert "ZZZ" in resp.json()["detail"]


def test_endpoint_happy_path_returns_grade_and_subscores(client: TestClient):
    instrument = type("I", (), {"id": uuid.uuid4()})()
    front = type("C", (), {"id": uuid.uuid4(), "contract_code": "NGM26"})()
    fake_result = sq.SignalQualityResult(
        grade="A",
        total_score=82,
        sub_scores={
            "input_diversity": 30,
            "model_agreement": 25,
            "regime_stability": 15,
            "time_to_decision": 12,
        },
        sub_score_max={
            "input_diversity": 30,
            "model_agreement": 25,
            "regime_stability": 25,
            "time_to_decision": 20,
        },
        detail={"input_diversity": "high"},
    )

    with patch(
        "apps.api.routers.signal_quality.instr_repo.get_by_symbol",
        new=AsyncMock(return_value=instrument),
    ), patch(
        "apps.api.routers.signal_quality.contract_repo.get_front_month",
        new=AsyncMock(return_value=front),
    ), patch(
        "apps.api.routers.signal_quality.get_latest_closes",
        new=AsyncMock(return_value=[3.0] * 100),
    ), patch(
        "apps.api.routers.signal_quality.run_all",
        new=AsyncMock(return_value=[]),
    ), patch(
        "apps.api.routers.signal_quality.compute_ensemble",
        new=lambda results: {"agreement": {"input_diversity": "high"}},
    ), patch(
        "apps.api.routers.signal_quality.compute_grade",
        new=AsyncMock(return_value=fake_result),
    ):
        resp = client.get("/v1/signal-quality?symbol=NG")
    assert resp.status_code == 200
    body = resp.json()
    assert body["grade"] == "A"
    assert body["total_score"] == 82
    assert body["sub_scores"]["input_diversity"] == 30
    assert body["sub_score_max"]["regime_stability"] == 25
    assert body["detail"]["input_diversity"] == "high"
