"""Phase 25 — seasonality transform + endpoint."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.api.services.seasonality import build_seasonality
from apps.api.src.main import app


def _bar(dt: datetime, close: float):
    return {"ts": dt, "open": close, "high": close, "low": close, "close": close, "volume": 100}


def _three_years():
    bars = []
    for year in (2024, 2025, 2026):
        for month in range(1, 13):
            bars.append(_bar(datetime(year, month, 15), 3.0 + month * 0.1))
    return bars


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_groups_by_year_and_aligns_md():
    out = build_seasonality(_three_years())
    assert [y["year"] for y in out["years"]] == [2024, 2025, 2026]
    # Each year has 12 monthly points, md formatted MM-DD.
    assert len(out["years"][0]["points"]) == 12
    assert out["years"][0]["points"][0]["md"] == "01-15"


def test_average_is_cross_year_mean():
    out = build_seasonality(_three_years())
    jan = next(p for p in out["average"] if p["md"] == "01-15")
    # All three years have close 3.1 in January → average 3.1
    assert jan["v"] == pytest.approx(3.1)


def test_max_years_keeps_most_recent():
    out = build_seasonality(_three_years(), max_years=2)
    assert [y["year"] for y in out["years"]] == [2025, 2026]


def test_endpoint_404_unknown_contract(client: TestClient):
    with patch(
        "apps.api.routers.chart.contract_repo.get_by_code",
        new=AsyncMock(return_value=None),
    ):
        resp = client.get("/v1/chart/seasonality?contract_code=ZZZ99")
    assert resp.status_code == 404


def test_endpoint_returns_years_and_average(client: TestClient):
    market = MagicMock()
    market.get_bars = AsyncMock(return_value=_three_years())
    contract = type("C", (), {"expiry_date": None})()
    with patch(
        "apps.api.routers.chart.contract_repo.get_by_code",
        new=AsyncMock(return_value=contract),
    ), patch("apps.api.routers.chart.get_market", new=lambda: market):
        resp = client.get("/v1/chart/seasonality?contract_code=NGM26&years=3")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["years"]) == 3
    assert body["average"]
