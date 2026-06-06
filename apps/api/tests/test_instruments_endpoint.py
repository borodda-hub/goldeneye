"""Phase 14 Step 6 — /v1/instruments route tests."""
from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.api.src.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _no_watchlist_cache():
    """The /v1/instruments route returns a cached Redis 'watchlist:v1' payload
    before it ever calls the repo. These tests exercise the router's repo →
    quote-shaping logic via mocks, so disable the cache to keep them hermetic
    regardless of whatever the local Redis happens to hold."""
    with patch(
        "apps.api.routers.instruments._get_cache", return_value=None
    ):
        yield


def _instr(symbol: str, name: str, meta: dict | None = None) -> Any:
    return type(
        "I",
        (),
        {
            "id": uuid.uuid4(),
            "symbol": symbol,
            "name": name,
            "asset_class": "commodity",
            "currency": "USD",
            "unit": "barrel" if symbol == "CL" else "MMBtu",
            "metadata_": meta or {},
        },
    )()


def _contract(code: str) -> Any:
    return type("C", (), {"id": uuid.uuid4(), "contract_code": code})()


def test_lists_two_instruments_with_quotes(client: TestClient):
    ng = _instr("NG", "Henry Hub Natural Gas", {"yahoo_ticker": "NG=F"})
    cl = _instr("CL", "WTI Crude Oil", {"yahoo_ticker": "CL=F"})

    async def fake_get_all(session):
        return [cl, ng]  # router sorts NG first regardless of order

    async def fake_front(session, instrument_id):
        if instrument_id == ng.id:
            return _contract("NGM26")
        return _contract("CLN26")

    async def fake_closes(session, *, contract_id, contract_code, n=2):
        # Helper returns oldest→newest. So prev=3.15, last=3.20.
        return [3.15, 3.20] if contract_id else []

    with patch(
        "apps.api.routers.instruments.instr_repo.get_all",
        new=AsyncMock(side_effect=fake_get_all),
    ), patch(
        "apps.api.routers.instruments.contract_repo.get_front_month",
        new=AsyncMock(side_effect=fake_front),
    ), patch(
        "apps.api.routers.instruments.get_latest_closes",
        new=AsyncMock(side_effect=fake_closes),
    ):
        resp = client.get("/v1/instruments")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["instruments"]) == 2
    # NG first regardless of repo ordering.
    assert body["instruments"][0]["symbol"] == "NG"
    assert body["instruments"][1]["symbol"] == "CL"
    # Quote shape is present + populated.
    ng_quote = body["instruments"][0]["quote"]
    assert ng_quote["last_price"] == 3.20
    assert ng_quote["change_abs"] == pytest.approx(0.05)
    assert ng_quote["change_pct"] == pytest.approx(0.05 / 3.15)
    assert ng_quote["front_month_code"] == "NGM26"


def test_quote_null_when_no_front_month(client: TestClient):
    cl = _instr("CL", "WTI Crude Oil")
    with patch(
        "apps.api.routers.instruments.instr_repo.get_all",
        new=AsyncMock(return_value=[cl]),
    ), patch(
        "apps.api.routers.instruments.contract_repo.get_front_month",
        new=AsyncMock(return_value=None),
    ):
        resp = client.get("/v1/instruments")
    assert resp.status_code == 200
    cl_row = resp.json()["instruments"][0]
    assert cl_row["quote"]["last_price"] is None
    assert cl_row["quote"]["front_month_code"] is None


def test_quote_partial_when_only_one_close(client: TestClient):
    """Change_abs/change_pct can't be computed from 1 close — should be null."""
    ng = _instr("NG", "NG")
    with patch(
        "apps.api.routers.instruments.instr_repo.get_all",
        new=AsyncMock(return_value=[ng]),
    ), patch(
        "apps.api.routers.instruments.contract_repo.get_front_month",
        new=AsyncMock(return_value=_contract("NGM26")),
    ), patch(
        "apps.api.routers.instruments.get_latest_closes",
        new=AsyncMock(return_value=[3.20]),
    ):
        resp = client.get("/v1/instruments")
    ng_quote = resp.json()["instruments"][0]["quote"]
    assert ng_quote["last_price"] == 3.20
    assert ng_quote["change_abs"] is None
    assert ng_quote["change_pct"] is None


def test_price_lookup_failure_doesnt_break_response(client: TestClient):
    ng = _instr("NG", "NG")
    with patch(
        "apps.api.routers.instruments.instr_repo.get_all",
        new=AsyncMock(return_value=[ng]),
    ), patch(
        "apps.api.routers.instruments.contract_repo.get_front_month",
        new=AsyncMock(return_value=_contract("NGM26")),
    ), patch(
        # Helper swallows internal failures and returns [] — verify the
        # router degrades gracefully when the lookup yields nothing.
        "apps.api.routers.instruments.get_latest_closes",
        new=AsyncMock(return_value=[]),
    ):
        resp = client.get("/v1/instruments")
    assert resp.status_code == 200
    ng_quote = resp.json()["instruments"][0]["quote"]
    assert ng_quote["last_price"] is None


def test_metadata_surfaced_under_metadata_key(client: TestClient):
    """ORM column is metadata_, API surfaces it as metadata. Don't leak the underscore."""
    ng = _instr("NG", "NG", {"yahoo_ticker": "NG=F", "cftc_market_code": "023651"})
    with patch(
        "apps.api.routers.instruments.instr_repo.get_all",
        new=AsyncMock(return_value=[ng]),
    ), patch(
        "apps.api.routers.instruments.contract_repo.get_front_month",
        new=AsyncMock(return_value=None),
    ):
        resp = client.get("/v1/instruments")
    body = resp.json()["instruments"][0]
    assert "metadata_" not in body
    assert body["metadata"]["yahoo_ticker"] == "NG=F"
    assert body["metadata"]["cftc_market_code"] == "023651"
