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
    forecast_vol_correlation,
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


def _garch(
    n: int,
    omega: float = 4e-6,
    alpha: float = 0.08,
    beta: float = 0.90,
    seed: int = 3,
    start: float = 100.0,
) -> list[float]:
    """GARCH(1,1) series with volatility *clustering* — the regime a real commodity has.

    Unlike ``_gbm`` (constant vol), forward vol is partly predictable here, so the EWMA
    forecaster's forward-vol correlation should be clearly positive.
    """
    rng = np.random.default_rng(seed)
    var = omega / (1.0 - alpha - beta)
    rets = np.empty(n)
    for i in range(n):
        r = float(np.sqrt(var)) * rng.normal()
        rets[i] = r
        var = omega + alpha * r * r + beta * var
    return (start * np.exp(np.cumsum(rets))).tolist()


def _seeded_ng_daily_closes() -> list[float]:
    """The actual seeded NG front-month daily closes (regime-switching GBM, deterministic).

    Locking calibration against the real series we ship — not a proxy — so a change to the
    seed generator that breaks the vol model's calibration assumption fails here.
    """
    from apps.api.seeds.price_generator import generate

    bars = generate()["bars"]
    return [b["close"] for b in bars if b["resolution"] == "1d"]


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
    # Bands must actually contain the move near their nominal rate. On normal (constant-vol)
    # data the empirical tail quantiles ≈ the normal z, so both bands sit near nominal.
    assert 0.73 <= cov["cov80"] <= 0.87
    assert 0.90 <= cov["cov95"] <= 0.98
    # n_eff reports independent (non-overlapping) windows, < the overlapping trial count.
    assert isinstance(cov["n_eff"], int) and cov["n_eff"] > 0


def test_coverage_thin_history_returns_none_levels():
    cov = walk_forward_coverage([100.0] * 12, "1w")
    assert cov == {"cov80": None, "cov95": None, "n_eff": 0}


# ── Calibration + edge, on the REAL seeded NG series (not a proxy) ─────────────


def test_coverage_and_correlation_on_real_seeded_ng():
    """The headline Phase-30a claim, locked against the actual shipped NG series."""
    closes = _seeded_ng_daily_closes()
    assert len(closes) > 500
    cov = walk_forward_coverage(closes, "1w")
    # 80% band genuinely covers ~80% of moves. The 30c empirical-tail band runs a touch
    # wider than the old normal-z on this short (n≈729) regime-switching series, so the
    # upper tolerance is a little looser here than on the long real series.
    assert cov["cov80"] is not None and 0.76 <= cov["cov80"] <= 0.86
    # 30c lock: the 95% band reaches near-nominal coverage via empirical fat-tail
    # quantiles (the old normal-z version ran light at ~0.92 on real fat tails).
    assert cov["cov95"] is not None and 0.90 <= cov["cov95"] <= 0.99
    # The forecaster carries real forward-vol information (measured ≈0.42).
    corr = forecast_vol_correlation(closes, "1w")
    assert corr is not None and corr > 0.2


# ── The edge is a real mechanism, not a fitting artifact ──────────────────────


def test_forward_vol_correlation_positive_under_clustering():
    """Clustering (GARCH) → forecast correlates with realized forward vol across seeds."""
    for seed in (1, 2, 3, 4, 5):
        corr = forecast_vol_correlation(_garch(1500, seed=seed), "1w")
        assert corr is not None and corr > 0.2, f"seed {seed}: {corr}"


def test_forward_vol_correlation_near_zero_on_constant_vol():
    """Constant vol → no forward-vol info → correlation near zero (no spurious edge)."""
    for seed in (7, 11, 21):
        corr = forecast_vol_correlation(_gbm(1500, seed=seed), "1w")
        assert corr is not None and abs(corr) < 0.15, f"seed {seed}: {corr}"


def test_coverage_robust_across_vol_regimes():
    """80% coverage stays near nominal across diverse clustering regimes (cross-commodity
    robustness proxy — the live NG/CL/HO/RB/GC/SI numbers are validated via the endpoint)."""
    for seed in (1, 2, 3, 4, 5):
        cov = walk_forward_coverage(_garch(1500, seed=seed), "1w")
        assert cov["cov80"] is not None and 0.74 <= cov["cov80"] <= 0.86, f"seed {seed}: {cov}"
        # 30c lock: even with fat-tailed clustering, the empirical-tail 95% band stays
        # near nominal (the old normal-z band under-covered here).
        assert cov["cov95"] is not None and cov["cov95"] >= 0.90, f"seed {seed}: {cov}"


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
    assert "n_eff" in body["coverage"]  # honest effective-sample-size readout
    assert "forward_vol_corr" in body  # forward-vol correlation readout
    # the honest point-forecast caveat is surfaced
    assert any("not reliable out-of-sample" in c for c in body["safety"]["caveats"])
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
