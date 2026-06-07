"""Phase 30a — volatility & range forecast.

Unit-tests the EWMA range forecaster and locks the calibration gate: on synthetic
constant-vol data the walk-forward 80%/95% interval coverage must land near nominal.
This is the methodology lock — a future change that breaks band calibration fails here.
Plus an endpoint happy-path / error-path check.
"""
from __future__ import annotations

import uuid
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

from apps.api.services.models.vol_range import (
    RangeForecast,
    predict,
    walk_forward_coverage,
)
from apps.api.src.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _gbm(n: int, sigma: float = 0.02, seed: int = 7, start: float = 100.0) -> list[float]:
    """Constant-vol geometric series: log-returns ~ Normal(0, sigma)."""
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0, sigma, n)
    return (start * np.exp(np.cumsum(rets))).tolist()


# ── Forecaster ──────────────────────────────────────────────────────────────


def test_predict_returns_symmetric_widening_bands():
    out = predict(_gbm(120), "1w")
    assert isinstance(out, RangeForecast)
    assert out.sigma_daily > 0 and out.sigma_horizon > out.sigma_daily
    # symmetric around 0 (no directional claim)
    assert out.band80_low_pct == pytest.approx(-out.band80_high_pct)
    assert out.band95_low_pct == pytest.approx(-out.band95_high_pct)
    # 95% band is wider than 80%
    assert out.band95_high_pct > out.band80_high_pct


def test_longer_horizon_widens_band():
    closes = _gbm(150)
    d1 = predict(closes, "1d")
    w1 = predict(closes, "1w")
    assert w1 is not None and d1 is not None
    assert w1.sigma_horizon > d1.sigma_horizon
    assert w1.band80_high_pct > d1.band80_high_pct


def test_insufficient_history_returns_none():
    assert predict([100.0] * 10, "1w") is None


def test_rejects_nonpositive_closes():
    closes = _gbm(80)
    closes[40] = 0.0
    assert predict(closes, "1w") is None


# ── Calibration gate (the lock) ───────────────────────────────────────────────


def test_walk_forward_coverage_near_nominal_on_constant_vol():
    closes = _gbm(1500, sigma=0.02, seed=11)
    cov = walk_forward_coverage(closes, "1w")
    assert cov["cov80"] is not None and cov["cov95"] is not None
    # Bands must actually contain the move near their nominal rate (normal data → no
    # fat-tail penalty, so 95% should also be close).
    assert 0.73 <= cov["cov80"] <= 0.87
    assert cov["cov95"] >= 0.88


def test_coverage_thin_history_returns_none_levels():
    cov = walk_forward_coverage([100.0] * 12, "1w")
    assert cov == {"cov80": None, "cov95": None}


# ── Endpoint (hermetic — DB calls patched so tests don't depend on a live DB) ──

_FAKE_INSTR = SimpleNamespace(id=uuid.uuid4())
_FAKE_FRONT = SimpleNamespace(id=uuid.uuid4(), contract_code="NGX26")


def _patch_db(closes: list[float]) -> ExitStack:
    stack = ExitStack()
    stack.enter_context(
        patch(
            "apps.api.routers.forecast.instr_repo.get_by_symbol",
            new=AsyncMock(return_value=_FAKE_INSTR),
        )
    )
    stack.enter_context(
        patch(
            "apps.api.routers.forecast.contract_repo.get_front_month",
            new=AsyncMock(return_value=_FAKE_FRONT),
        )
    )
    stack.enter_context(
        patch(
            "apps.api.routers.forecast.get_latest_closes",
            new=AsyncMock(return_value=closes),
        )
    )
    return stack


def test_range_endpoint_happy_path(client: TestClient):
    with _patch_db(_gbm(150)):
        resp = client.get("/v1/forecast/range", params={"symbol": "NG", "horizon": "1w"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["horizon"] == "1w"
    rng = body["range"]
    assert rng["band95_high_pct"] > rng["band80_high_pct"] > 0
    assert "cov80" in body["coverage"]
    assert body["safety"]["disclaimer"]  # safety envelope present


def test_range_endpoint_rejects_bad_horizon(client: TestClient):
    resp = client.get("/v1/forecast/range", params={"symbol": "NG", "horizon": "42y"})
    assert resp.status_code == 422


def test_range_endpoint_unknown_symbol_404(client: TestClient):
    with patch(
        "apps.api.routers.forecast.instr_repo.get_by_symbol",
        new=AsyncMock(return_value=None),
    ):
        resp = client.get("/v1/forecast/range", params={"symbol": "ZZZ"})
    assert resp.status_code == 404


def test_range_endpoint_insufficient_history_422(client: TestClient):
    with _patch_db([100.0, 101.0, 102.0]):
        resp = client.get("/v1/forecast/range", params={"symbol": "NG"})
    assert resp.status_code == 422
