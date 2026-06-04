"""Phase 18 — positioning service + endpoint tests."""
from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.api.services import positioning as pos
from apps.api.src.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _instrument(symbol: str, code: str | None):
    meta = {"cftc_market_code": code} if code else {}
    return type("I", (), {"id": uuid.uuid4(), "symbol": symbol, "metadata_": meta})()


def _cot(net: int, oi: int, d: date):
    return type(
        "C",
        (),
        {
            "managed_money_net": net,
            "managed_money_long": net + 100,
            "managed_money_short": 100,
            "open_interest_total": oi,
            "report_date": d,
            "release_date": d,
            "source": "CFTC_PRE",
        },
    )()


# ── Service logic ──────────────────────────────────────────────────────────


async def test_available_with_wow_delta():
    rows = [_cot(16594, 1_378_398, date(2026, 5, 5)), _cot(26078, 1_400_000, date(2026, 4, 28))]
    with patch(
        "apps.api.services.positioning.cot_repo.get_recent",
        new=AsyncMock(return_value=rows),
    ):
        out = await pos.get_positioning(MagicMock(), _instrument("NG", "023651"))
    assert out["available"] is True
    assert out["managed_money_net"] == 16594
    assert out["mm_net_delta"] == 16594 - 26078
    assert out["open_interest_total"] == 1_378_398


async def test_no_market_code_unavailable():
    out = await pos.get_positioning(MagicMock(), _instrument("ES", None))
    assert out["available"] is False
    assert out["managed_money_net"] is None


async def test_no_cot_rows_unavailable():
    with patch(
        "apps.api.services.positioning.cot_repo.get_recent",
        new=AsyncMock(return_value=[]),
    ):
        out = await pos.get_positioning(MagicMock(), _instrument("GC", "088691"))
    assert out["available"] is False


async def test_single_row_has_no_delta():
    with patch(
        "apps.api.services.positioning.cot_repo.get_recent",
        new=AsyncMock(return_value=[_cot(5000, 300_000, date(2026, 5, 5))]),
    ):
        out = await pos.get_positioning(MagicMock(), _instrument("HO", "022651"))
    assert out["available"] is True
    assert out["mm_net_delta"] is None


# ── Endpoint ───────────────────────────────────────────────────────────────


def test_endpoint_404_unknown_symbol(client: TestClient):
    with patch(
        "apps.api.routers.positioning.instr_repo.get_by_symbol",
        new=AsyncMock(return_value=None),
    ):
        resp = client.get("/v1/positioning?symbol=ZZZ")
    assert resp.status_code == 404


def test_endpoint_happy_path(client: TestClient):
    instrument = _instrument("NG", "023651")
    payload = {"symbol": "NG", "available": True, "managed_money_net": 16594,
               "mm_net_delta": -9484, "open_interest_total": 1_378_398}
    with patch(
        "apps.api.routers.positioning.instr_repo.get_by_symbol",
        new=AsyncMock(return_value=instrument),
    ), patch(
        "apps.api.routers.positioning.get_positioning",
        new=AsyncMock(return_value=payload),
    ):
        resp = client.get("/v1/positioning?symbol=NG")
    assert resp.status_code == 200
    assert resp.json()["available"] is True
    assert resp.json()["managed_money_net"] == 16594
