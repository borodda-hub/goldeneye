"""Tests for GET /v1/chart/indicators (Phase 15 step 15b)."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.api.src.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _instr(symbol: str) -> Any:
    return type("I", (), {"id": uuid.uuid4(), "symbol": symbol})()


def _contract(code: str) -> Any:
    return type("C", (), {"id": uuid.uuid4(), "contract_code": code})()


def _bars(n: int = 60, with_volume: bool = True) -> list[dict[str, Any]]:
    start = datetime(2026, 1, 1)
    out: list[dict[str, Any]] = []
    for i in range(n):
        out.append(
            {
                "ts": start + timedelta(days=i),
                "contract_code": "TST",
                "resolution": "1d",
                "open": 3.0 + i * 0.01,
                "high": 3.1 + i * 0.01,
                "low": 2.9 + i * 0.01,
                "close": 3.0 + i * 0.01,
                "volume": (1000 + i) if with_volume else None,
                "source": "mock",
            }
        )
    return out


def _market_mock(bars: list[dict[str, Any]]) -> Any:
    """A market adapter stand-in whose get_bars returns the supplied list."""
    m = type("MarketStub", (), {})()
    m.get_bars = AsyncMock(return_value=bars)
    return m


# ---------- happy path ----------


def test_happy_path_multi_indicator(client: TestClient):
    ng = _instr("NG")
    with patch(
        "apps.api.routers.indicators.instr_repo.get_by_symbol",
        new=AsyncMock(return_value=ng),
    ), patch(
        "apps.api.routers.indicators.contract_repo.get_front_month",
        new=AsyncMock(return_value=_contract("NGM26")),
    ), patch(
        "apps.api.routers.indicators.get_market",
        return_value=_market_mock(_bars(60)),
    ), patch(
        "apps.api.services.indicators.cache._get_default_client", return_value=None
    ):
        resp = client.get("/v1/chart/indicators?symbol=NG&spec=ema:21,sma:5")

    assert resp.status_code == 200
    body = resp.json()
    assert body["symbol"] == "NG"
    assert len(body["indicators"]) == 2

    by_type = {ind["type"]: ind for ind in body["indicators"]}
    assert by_type["ema"]["params"]["period"] == 21
    assert by_type["sma"]["params"]["period"] == 5
    # Each indicator returns one point per input bar
    assert len(by_type["ema"]["points"]) == 60
    assert len(by_type["sma"]["points"]) == 60
    # SMA(5) defined from index 4 onward
    assert by_type["sma"]["points"][3]["v"] is None
    assert by_type["sma"]["points"][4]["v"] is not None


def test_default_source_is_close(client: TestClient):
    ng = _instr("NG")
    with patch(
        "apps.api.routers.indicators.instr_repo.get_by_symbol",
        new=AsyncMock(return_value=ng),
    ), patch(
        "apps.api.routers.indicators.contract_repo.get_front_month",
        new=AsyncMock(return_value=_contract("NGM26")),
    ), patch(
        "apps.api.routers.indicators.get_market",
        return_value=_market_mock(_bars(20)),
    ), patch(
        "apps.api.services.indicators.cache._get_default_client", return_value=None
    ):
        resp = client.get("/v1/chart/indicators?symbol=NG&spec=sma:3")
    assert resp.status_code == 200
    assert resp.json()["indicators"][0]["params"]["source"] == "close"


def test_explicit_source_passes_through(client: TestClient):
    ng = _instr("NG")
    with patch(
        "apps.api.routers.indicators.instr_repo.get_by_symbol",
        new=AsyncMock(return_value=ng),
    ), patch(
        "apps.api.routers.indicators.contract_repo.get_front_month",
        new=AsyncMock(return_value=_contract("NGM26")),
    ), patch(
        "apps.api.routers.indicators.get_market",
        return_value=_market_mock(_bars(20)),
    ), patch(
        "apps.api.services.indicators.cache._get_default_client", return_value=None
    ):
        resp = client.get("/v1/chart/indicators?symbol=NG&spec=sma:3:hl2")
    assert resp.status_code == 200
    assert resp.json()["indicators"][0]["params"]["source"] == "hl2"


def test_empty_bars_returns_empty_indicators(client: TestClient):
    ng = _instr("NG")
    with patch(
        "apps.api.routers.indicators.instr_repo.get_by_symbol",
        new=AsyncMock(return_value=ng),
    ), patch(
        "apps.api.routers.indicators.contract_repo.get_front_month",
        new=AsyncMock(return_value=_contract("NGM26")),
    ), patch(
        "apps.api.routers.indicators.get_market",
        return_value=_market_mock([]),
    ):
        resp = client.get("/v1/chart/indicators?symbol=NG&spec=ema:21")
    assert resp.status_code == 200
    assert resp.json() == {"symbol": "NG", "indicators": []}


# ---------- error paths ----------


def test_unknown_indicator_type_400(client: TestClient):
    resp = client.get("/v1/chart/indicators?symbol=NG&spec=bollinger:20")
    assert resp.status_code == 400
    assert "unknown indicator type" in resp.json()["detail"]


def test_unknown_symbol_404(client: TestClient):
    with patch(
        "apps.api.routers.indicators.instr_repo.get_by_symbol",
        new=AsyncMock(return_value=None),
    ):
        resp = client.get("/v1/chart/indicators?symbol=ZZZ&spec=ema:21")
    assert resp.status_code == 404
    assert "unknown symbol" in resp.json()["detail"]


def test_no_front_month_404(client: TestClient):
    with patch(
        "apps.api.routers.indicators.instr_repo.get_by_symbol",
        new=AsyncMock(return_value=_instr("NG")),
    ), patch(
        "apps.api.routers.indicators.contract_repo.get_front_month",
        new=AsyncMock(return_value=None),
    ):
        resp = client.get("/v1/chart/indicators?symbol=NG&spec=ema:21")
    assert resp.status_code == 404
    assert "front-month" in resp.json()["detail"]


def test_period_out_of_range_400(client: TestClient):
    resp = client.get("/v1/chart/indicators?symbol=NG&spec=ema:1000")
    assert resp.status_code == 400
    assert "out of range" in resp.json()["detail"]


def test_period_too_small_400(client: TestClient):
    resp = client.get("/v1/chart/indicators?symbol=NG&spec=ema:1")
    assert resp.status_code == 400
    assert "out of range" in resp.json()["detail"]


def test_vwma_without_volume_400(client: TestClient):
    with patch(
        "apps.api.routers.indicators.instr_repo.get_by_symbol",
        new=AsyncMock(return_value=_instr("NG")),
    ), patch(
        "apps.api.routers.indicators.contract_repo.get_front_month",
        new=AsyncMock(return_value=_contract("NGM26")),
    ), patch(
        "apps.api.routers.indicators.get_market",
        return_value=_market_mock(_bars(20, with_volume=False)),
    ), patch(
        "apps.api.services.indicators.cache._get_default_client", return_value=None
    ):
        resp = client.get("/v1/chart/indicators?symbol=NG&spec=vwma:5")
    assert resp.status_code == 400
    assert "VWMA requires" in resp.json()["detail"]


def test_bad_period_format_400(client: TestClient):
    resp = client.get("/v1/chart/indicators?symbol=NG&spec=ema:abc")
    assert resp.status_code == 400
    assert "bad period" in resp.json()["detail"]


# ---------- cache hit path ----------


def test_second_call_serves_from_cache(client: TestClient):
    """Cache: second identical call short-circuits compute via Redis-like client."""

    class FakeRedis:
        def __init__(self) -> None:
            self.store: dict[str, str] = {}
            self.gets = 0
            self.sets = 0

        async def get(self, key: str) -> Any:
            self.gets += 1
            return self.store.get(key)

        async def set(self, key: str, value: str, ex: int | None = None) -> Any:
            self.sets += 1
            self.store[key] = value

    fake = FakeRedis()
    ng = _instr("NG")
    bars = _bars(30)

    with patch(
        "apps.api.routers.indicators.instr_repo.get_by_symbol",
        new=AsyncMock(return_value=ng),
    ), patch(
        "apps.api.routers.indicators.contract_repo.get_front_month",
        new=AsyncMock(return_value=_contract("NGM26")),
    ), patch(
        "apps.api.routers.indicators.get_market",
        return_value=_market_mock(bars),
    ), patch(
        "apps.api.services.indicators.cache._get_default_client", return_value=fake
    ):
        url = (
            "/v1/chart/indicators?symbol=NG&spec=sma:5"
            "&from=2026-01-01T00:00:00&to=2026-02-01T00:00:00"
        )
        r1 = client.get(url)
        r2 = client.get(url)

    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json() == r2.json()
    assert fake.sets == 1  # only the miss writes
    assert fake.gets == 2  # both calls read
