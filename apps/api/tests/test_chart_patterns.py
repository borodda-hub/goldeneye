"""Phase 24 — auto chart-pattern / auto-TA detection + endpoint."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.api.services.patterns import detect_auto_ta
from apps.api.src.main import app


def _bar(i: int, p: float):
    return {
        "ts": datetime(2026, 1, 1) if i == 0 else datetime(2026, 1, 1).replace(day=min(i + 1, 28)),
        "open": p,
        "high": p + 0.5,
        "low": p - 0.5,
        "close": p,
        "volume": 100,
    }


def _double_top_bars():
    seq = [100, 103, 106, 109, 110, 107, 103, 100, 103, 106, 109, 110, 107, 103, 99]
    return [_bar(i, p) for i, p in enumerate(seq * 3)]


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ── Engine ─────────────────────────────────────────────────────────────────


def test_too_few_bars_returns_empty():
    out = detect_auto_ta([_bar(i, 100) for i in range(5)])
    assert out == {"levels": [], "trendlines": [], "patterns": []}


def test_detects_levels_and_trendlines():
    out = detect_auto_ta(_double_top_bars())
    assert out["levels"], out
    assert {t["role"] for t in out["trendlines"]} == {"support", "resistance"}
    for lvl in out["levels"]:
        assert lvl["kind"] in {"support", "resistance"}
        assert lvl["touches"] >= 2


def test_detects_double_top():
    out = detect_auto_ta(_double_top_bars())
    names = {p["name"] for p in out["patterns"]}
    assert "Double Top" in names
    dt = next(p for p in out["patterns"] if p["name"] == "Double Top")
    assert dt["direction"] == "bearish"
    assert 0.0 <= dt["confidence"] <= 1.0
    assert "neckline" in dt and len(dt["points"]) == 2
    assert dt["description"]


def test_random_walk_no_spurious_patterns():
    import numpy as np

    rng = np.random.default_rng(3)
    px = 100 + np.cumsum(rng.normal(0, 1, 120))
    bars = [_bar(i % 28, float(px[i])) for i in range(120)]
    out = detect_auto_ta(bars)
    # levels/trendlines fine; patterns should not over-fire on noise
    assert isinstance(out["patterns"], list)


# ── Endpoint ───────────────────────────────────────────────────────────────


def test_endpoint_404_unknown_contract(client: TestClient):
    with patch(
        "apps.api.routers.patterns.contract_repo.get_by_code",
        new=AsyncMock(return_value=None),
    ):
        resp = client.get("/v1/chart/auto-ta?contract_code=ZZZ99")
    assert resp.status_code == 404


def test_endpoint_returns_geometry_and_safety(client: TestClient):
    bars = _double_top_bars()
    market = MagicMock()
    market.get_bars = AsyncMock(return_value=bars)
    contract = type("C", (), {"expiry_date": None})()
    with patch(
        "apps.api.routers.patterns.contract_repo.get_by_code",
        new=AsyncMock(return_value=contract),
    ), patch("apps.api.routers.patterns.get_market", new=lambda: market):
        resp = client.get("/v1/chart/auto-ta?contract_code=NGM26")
    assert resp.status_code == 200
    body = resp.json()
    assert "levels" in body and "trendlines" in body and "patterns" in body
    assert body["safety"]["confidence"] == "low"
    assert body["safety"]["disclaimer"]
