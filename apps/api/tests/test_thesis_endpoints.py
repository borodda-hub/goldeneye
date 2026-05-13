"""Phase 12 Step 2 — REST endpoint tests for the Working Thesis card.

Covers:
- GET /v1/thesis/current (200 + 404)
- GET /v1/thesis/seed (no data + with forecasts)
- POST /v1/thesis (happy path + validation rejections)
- PATCH /v1/thesis/{id} (happy path + 404 + 409 on deactivated rows)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.api.models.orm.theses import Thesis
from apps.api.src.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _make_thesis(
    *,
    statement: str = "Cold snap sustains storage draws.",
    conviction: int = 70,
    active: bool = True,
) -> Thesis:
    t = Thesis(
        id=uuid.uuid4(),
        instrument_code="NG",
        statement=statement,
        supporting_evidence=[
            {"factor": "weather", "weight": 0.6, "note": "", "source": "moving_average_directional"}
        ],
        contradicting_evidence=[
            {"factor": "lng_export_dip", "weight": 0.3, "note": "", "source": "volatility_regime"}
        ],
        missing_data=["EIA Weekly Storage"],
        conviction_pct=conviction,
        active=active,
    )
    t.created_at = datetime(2026, 5, 12, 12, 0, 0)
    t.updated_at = datetime(2026, 5, 12, 12, 0, 0)
    return t


def _fake_forecast(model_name: str, supporting: list[dict], contradicting: list[dict]) -> Any:
    return type(
        "F",
        (),
        {
            "model_name": model_name,
            "supporting": supporting,
            "contradicting": contradicting,
        },
    )()


def _fake_scenario(data_needed: list[str]) -> Any:
    return type("S", (), {"result": {"data_needed_to_validate": data_needed}})()


# ── GET /v1/thesis/current ────────────────────────────────────────────────


def test_current_returns_404_when_none(client: TestClient):
    with patch(
        "apps.api.routers.thesis.theses_repo.get_active",
        new=AsyncMock(return_value=None),
    ):
        resp = client.get("/v1/thesis/current")
    assert resp.status_code == 404
    assert "No active thesis" in resp.json()["detail"]


def test_current_returns_thesis(client: TestClient):
    thesis = _make_thesis()
    with patch(
        "apps.api.routers.thesis.theses_repo.get_active",
        new=AsyncMock(return_value=thesis),
    ):
        resp = client.get("/v1/thesis/current")
    assert resp.status_code == 200
    body = resp.json()
    assert body["statement"] == "Cold snap sustains storage draws."
    assert body["conviction_pct"] == 70
    assert body["active"] is True
    assert body["instrument_code"] == "NG"
    assert body["id"] == str(thesis.id)


# ── GET /v1/thesis/seed ───────────────────────────────────────────────────


def test_seed_returns_fallback_when_no_data(client: TestClient):
    with patch(
        "apps.api.routers.thesis.instruments_repo.get_by_symbol",
        new=AsyncMock(return_value=None),
    ), patch(
        "apps.api.routers.thesis.scenarios_repo.get_recent",
        new=AsyncMock(return_value=[]),
    ):
        resp = client.get("/v1/thesis/seed")
    assert resp.status_code == 200
    body = resp.json()
    assert body["instrument_code"] == "NG"
    assert body["statement"] == ""
    assert body["conviction_pct"] == 50
    assert body["supporting_evidence"] == []
    assert body["contradicting_evidence"] == []
    # Static fallback for missing_data always present.
    assert any("EIA Weekly Storage" in s for s in body["missing_data"])
    assert any("NWS" in s for s in body["missing_data"])
    assert any("CFTC" in s for s in body["missing_data"])


def test_seed_aggregates_evidence_from_forecasts(client: TestClient):
    instrument = type("I", (), {"id": uuid.uuid4()})()
    forecasts = [
        _fake_forecast(
            "moving_average_directional",
            supporting=[
                {"factor": "weather_demand", "weight": 0.5, "note": ""},
                {"factor": "storage_draw", "weight": 0.4, "note": ""},
            ],
            contradicting=[{"factor": "production_up", "weight": 0.2, "note": ""}],
        ),
        _fake_forecast(
            "volatility_regime",
            supporting=[
                # Duplicate factor — should be deduped, keeping the higher weight.
                {"factor": "weather_demand", "weight": 0.7, "note": ""},
            ],
            contradicting=[],
        ),
    ]
    scenarios = [_fake_scenario(["Custom validation point"])]

    with patch(
        "apps.api.routers.thesis.instruments_repo.get_by_symbol",
        new=AsyncMock(return_value=instrument),
    ), patch(
        "apps.api.routers.thesis.forecasts_repo.get_history",
        new=AsyncMock(return_value=forecasts),
    ), patch(
        "apps.api.routers.thesis.scenarios_repo.get_recent",
        new=AsyncMock(return_value=scenarios),
    ):
        resp = client.get("/v1/thesis/seed")
    assert resp.status_code == 200
    body = resp.json()
    factors = {e["factor"] for e in body["supporting_evidence"]}
    assert "weather_demand" in factors
    assert "storage_draw" in factors
    # Duplicate factor kept the higher weight (0.7 from vol_regime).
    weather = next(e for e in body["supporting_evidence"] if e["factor"] == "weather_demand")
    assert weather["weight"] == 0.7
    # Scenario's data_needed_to_validate appears first.
    assert body["missing_data"][0] == "Custom validation point"
    # Static fallback still present after the custom item.
    assert any("EIA Weekly Storage" in s for s in body["missing_data"])


# ── POST /v1/thesis ───────────────────────────────────────────────────────


def test_create_happy_path(client: TestClient):
    fresh = _make_thesis(statement="Storage draws should exceed 5-yr avg.", conviction=75)
    with patch(
        "apps.api.routers.thesis.theses_repo.replace_active",
        new=AsyncMock(return_value=fresh),
    ):
        resp = client.post(
            "/v1/thesis",
            json={
                "statement": "Storage draws should exceed 5-yr avg.",
                "supporting_evidence": [
                    {"factor": "weather", "weight": 0.6, "note": "northeast cold"}
                ],
                "contradicting_evidence": [],
                "missing_data": ["EIA Weekly Storage"],
                "conviction_pct": 75,
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["statement"] == "Storage draws should exceed 5-yr avg."
    assert body["conviction_pct"] == 75


def test_create_rejects_empty_statement(client: TestClient):
    resp = client.post(
        "/v1/thesis",
        json={
            "statement": "",
            "supporting_evidence": [],
            "contradicting_evidence": [],
            "missing_data": [],
            "conviction_pct": 50,
        },
    )
    assert resp.status_code == 422  # Pydantic min_length


def test_create_rejects_conviction_out_of_range(client: TestClient):
    resp = client.post(
        "/v1/thesis",
        json={
            "statement": "Valid statement.",
            "supporting_evidence": [],
            "contradicting_evidence": [],
            "missing_data": [],
            "conviction_pct": 101,
        },
    )
    assert resp.status_code == 422


def test_create_rejects_too_many_evidence_items(client: TestClient):
    resp = client.post(
        "/v1/thesis",
        json={
            "statement": "Valid.",
            "supporting_evidence": [
                {"factor": f"factor_{i}", "weight": 0.1, "note": ""} for i in range(25)
            ],
            "contradicting_evidence": [],
            "missing_data": [],
            "conviction_pct": 50,
        },
    )
    assert resp.status_code == 422


def test_create_repo_value_error_maps_to_400(client: TestClient):
    with patch(
        "apps.api.routers.thesis.theses_repo.replace_active",
        new=AsyncMock(side_effect=ValueError("statement must be non-empty")),
    ):
        resp = client.post(
            "/v1/thesis",
            json={
                "statement": "Some text.",
                "supporting_evidence": [],
                "contradicting_evidence": [],
                "missing_data": [],
                "conviction_pct": 50,
            },
        )
    assert resp.status_code == 400
    assert "statement" in resp.json()["detail"]


# ── PATCH /v1/thesis/{id} ─────────────────────────────────────────────────


def test_patch_404_when_missing(client: TestClient):
    with patch(
        "apps.api.routers.thesis.theses_repo.get_by_id",
        new=AsyncMock(return_value=None),
    ):
        resp = client.patch(
            f"/v1/thesis/{uuid.uuid4()}", json={"conviction_pct": 80}
        )
    assert resp.status_code == 404


def test_patch_409_on_deactivated_thesis(client: TestClient):
    inactive = _make_thesis(active=False)
    with patch(
        "apps.api.routers.thesis.theses_repo.get_by_id",
        new=AsyncMock(return_value=inactive),
    ):
        resp = client.patch(
            f"/v1/thesis/{inactive.id}", json={"conviction_pct": 80}
        )
    assert resp.status_code == 409
    assert "deactivated" in resp.json()["detail"]


def test_patch_happy_path(client: TestClient):
    existing = _make_thesis(conviction=50)
    # patch_active mutates and returns the same instance.
    async def fake_patch(session, thesis, patch_data):
        for k, v in patch_data.items():
            setattr(thesis, k, v)
        return thesis

    with patch(
        "apps.api.routers.thesis.theses_repo.get_by_id",
        new=AsyncMock(return_value=existing),
    ), patch(
        "apps.api.routers.thesis.theses_repo.patch_active",
        new=AsyncMock(side_effect=fake_patch),
    ):
        resp = client.patch(
            f"/v1/thesis/{existing.id}",
            json={"conviction_pct": 88, "statement": "Updated."},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["conviction_pct"] == 88
    assert body["statement"] == "Updated."


def test_patch_repo_value_error_maps_to_400(client: TestClient):
    existing = _make_thesis()
    with patch(
        "apps.api.routers.thesis.theses_repo.get_by_id",
        new=AsyncMock(return_value=existing),
    ), patch(
        "apps.api.routers.thesis.theses_repo.patch_active",
        new=AsyncMock(side_effect=ValueError("conviction_pct must be 0-100, got 150")),
    ):
        resp = client.patch(
            f"/v1/thesis/{existing.id}", json={"conviction_pct": 99}
        )
    assert resp.status_code == 400
    assert "conviction_pct" in resp.json()["detail"]
