"""Phase 21 — candlestick pattern engine + endpoint tests."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.api.services.patterns import detect_patterns
from apps.api.src.main import app


def _bar(ts, o, h, low, c, v=100):
    return {"ts": ts, "open": o, "high": h, "low": low, "close": c, "volume": v}


def _names(bars):
    return {d["name"] for d in detect_patterns(bars)}


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ── Engine ─────────────────────────────────────────────────────────────────


def test_too_few_bars_returns_empty():
    assert detect_patterns([_bar("d1", 1, 2, 0.5, 1.5)]) == []


def test_doji_detected():
    bars = [
        _bar("d1", 10, 11, 9, 10.5),
        _bar("d2", 10.5, 11, 10, 10.4),
        _bar("d3", 10.0, 10.8, 9.2, 10.02),  # tiny body → doji
    ]
    assert "Doji" in _names(bars)


def test_bullish_engulfing_detected():
    bars = [
        _bar("d1", 11, 11.2, 10.5, 10.6),
        _bar("d2", 10.6, 10.7, 9.8, 9.9),  # down bar
        _bar("d3", 9.7, 11.0, 9.6, 10.9),  # up bar engulfs prior body
    ]
    res = detect_patterns(bars)
    found = [d for d in res if d["name"] == "Bullish Engulfing"]
    assert found, res
    assert found[0]["direction"] == "bullish"
    assert 0 <= found[0]["strength"] <= 1


def test_bearish_engulfing_detected():
    bars = [
        _bar("d1", 9, 9.5, 8.8, 9.4),
        _bar("d2", 9.4, 10.2, 9.3, 10.1),  # up bar
        _bar("d3", 10.3, 10.4, 9.0, 9.2),  # down bar engulfs
    ]
    assert "Bearish Engulfing" in _names(bars)


def test_hammer_requires_downtrend():
    decline = [
        _bar(f"d{i}", px + 0.4, px + 0.6, px - 0.6, px - 0.4)
        for i, px in enumerate([110, 108, 106, 104, 102])
    ]
    hammer = _bar("d6", 100.0, 100.7, 98.0, 100.6)  # small body top, long lower wick
    assert "Hammer" in _names([*decline, hammer])


def test_three_white_soldiers_detected():
    bars = [
        _bar("d1", 10.0, 10.2, 9.9, 10.0),
        _bar("d2", 10.0, 10.6, 9.95, 10.5),
        _bar("d3", 10.3, 11.1, 10.25, 11.0),
        _bar("d4", 10.8, 11.6, 10.75, 11.5),
    ]
    assert "Three White Soldiers" in _names(bars)


def test_detections_carry_required_fields():
    bars = [
        _bar("d1", 11, 11.2, 10.5, 10.6),
        _bar("d2", 10.6, 10.7, 9.8, 9.9),
        _bar("d3", 9.7, 11.0, 9.6, 10.9),
    ]
    for d in detect_patterns(bars):
        assert set(d) >= {"ts", "code", "name", "direction", "strength", "meaning"}
        assert d["direction"] in {"bullish", "bearish", "neutral"}


# ── Endpoint ───────────────────────────────────────────────────────────────


def _fake_market(bars):
    market = MagicMock()
    market.get_bars = AsyncMock(return_value=bars)
    return market


def test_endpoint_404_unknown_contract(client: TestClient):
    with patch(
        "apps.api.routers.patterns.contract_repo.get_by_code",
        new=AsyncMock(return_value=None),
    ):
        resp = client.get("/v1/chart/patterns?contract_code=ZZZ99")
    assert resp.status_code == 404


def test_endpoint_returns_patterns_and_safety(client: TestClient):
    from datetime import datetime

    bars = [
        _bar(datetime(2026, 1, 1), 11, 11.2, 10.5, 10.6),
        _bar(datetime(2026, 1, 2), 10.6, 10.7, 9.8, 9.9),
        _bar(datetime(2026, 1, 3), 9.7, 11.0, 9.6, 10.9),
    ]
    contract = type("C", (), {"expiry_date": None})()
    with patch(
        "apps.api.routers.patterns.contract_repo.get_by_code",
        new=AsyncMock(return_value=contract),
    ), patch(
        "apps.api.routers.patterns.get_market",
        new=lambda: _fake_market(bars),
    ):
        resp = client.get("/v1/chart/patterns?contract_code=NGM26")
    assert resp.status_code == 200
    body = resp.json()
    assert any(p["name"] == "Bullish Engulfing" for p in body["patterns"])
    assert body["safety"]["confidence"] == "low"
    assert body["safety"]["caveats"]
    assert body["safety"]["disclaimer"]
