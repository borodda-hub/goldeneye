"""Phase 18 — fundamentals service + endpoint tests."""
from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.api.services import fundamentals as fund
from apps.api.src.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _gas_row():
    return type(
        "R",
        (),
        {
            "week_ending": date(2026, 5, 1),
            "total_lower_48_bcf": 1512.1,
            "net_change_bcf": 2.7,
            "surprise_bcf": -0.3,
            "five_year_avg_bcf": 1500.4,
            "source": "EIA",
        },
    )()


# ── Service logic ──────────────────────────────────────────────────────────


async def test_ng_returns_gas_storage():
    with patch(
        "apps.api.services.fundamentals.eia_repo.get_latest",
        new=AsyncMock(return_value=_gas_row()),
    ):
        out = await fund.get_fundamentals(MagicMock(), "NG")
    assert out["kind"] == "gas_storage"
    assert out["unit"] == "Bcf"
    assert out["latest"]["level"] == 1512.1
    assert out["latest"]["net_change"] == 2.7
    assert out["latest"]["five_year_avg"] == 1500.4
    assert out["empty_reason"] is None


async def test_petroleum_product_returns_stocks():
    adapter = MagicMock()
    adapter.get_latest_storage = AsyncMock(
        return_value={
            "week_ending": date(2026, 5, 29),
            "total_lower_48_bcf": 102301.0,
            "net_change_bcf": 1502.0,
            "surprise_bcf": 1502.0,
            "source": "eia_petroleum",
        }
    )
    with patch(
        "apps.api.services.fundamentals.get_energy", new=lambda s: adapter
    ):
        out = await fund.get_fundamentals(MagicMock(), "HO")
    assert out["kind"] == "petroleum_stocks"
    assert out["unit"] == "Mbbl"
    assert out["title"] == "Distillate Stocks"
    assert out["latest"]["level"] == 102301.0
    assert out["latest"]["five_year_avg"] is None


async def test_metal_returns_empty_state():
    out = await fund.get_fundamentals(MagicMock(), "GC")
    assert out["kind"] == "none"
    assert out["latest"] is None
    assert out["empty_reason"]


# ── Endpoint ───────────────────────────────────────────────────────────────


def test_endpoint_404_unknown_symbol(client: TestClient):
    with patch(
        "apps.api.routers.fundamentals.instr_repo.get_by_symbol",
        new=AsyncMock(return_value=None),
    ):
        resp = client.get("/v1/fundamentals?symbol=ZZZ")
    assert resp.status_code == 404
    assert "ZZZ" in resp.json()["detail"]


def test_endpoint_happy_path(client: TestClient):
    instrument = type("I", (), {"id": uuid.uuid4(), "symbol": "NG"})()
    payload = {
        "symbol": "NG",
        "kind": "gas_storage",
        "title": "Working Gas in Storage",
        "unit": "Bcf",
        "latest": {"as_of": "2026-05-01", "level": 1512.1, "net_change": 2.7,
                   "surprise": -0.3, "five_year_avg": 1500.4},
        "source": "EIA",
        "empty_reason": None,
    }
    with patch(
        "apps.api.routers.fundamentals.instr_repo.get_by_symbol",
        new=AsyncMock(return_value=instrument),
    ), patch(
        "apps.api.routers.fundamentals.get_fundamentals",
        new=AsyncMock(return_value=payload),
    ):
        resp = client.get("/v1/fundamentals?symbol=NG")
    assert resp.status_code == 200
    assert resp.json()["kind"] == "gas_storage"
    assert resp.json()["latest"]["level"] == 1512.1
