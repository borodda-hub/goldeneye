"""Phase 10 Step 3 — backtest endpoint tests.

Focused on the HTTP wrapper, validation, response shape, and persistence
plumbing. Engine internals are covered by test_backtest_engine.py and
look-ahead by test_backtest_lookahead.py.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.api.services.backtest import (
    SUPPORTED_MODELS,
    BacktestRow,
    BacktestSummary,
)
from apps.api.src.main import app


def _fake_instrument(symbol: str = "NG") -> Any:
    return type("I", (), {"id": uuid.uuid4(), "symbol": symbol})()


def _sample_row(generated_at: datetime, outcome: str = "hit") -> BacktestRow:
    return BacktestRow(
        generated_at=generated_at,
        model_name="moving_average_directional",
        horizon="1d",
        direction="bullish",
        confidence="medium",
        expected_pct=0.012,
        realized_pct=0.018,
        outcome=outcome,
        delta_from_expected_pct=0.006,
        vol_regime="normal",
        supporting=[{"factor": "sma_cross", "weight": 0.6, "note": ""}],
        contradicting=[{"factor": "rsi_overbought", "weight": 0.3, "note": ""}],
        inputs_used=["closes"],
    )


def _sample_summary(n: int = 3, scored: int = 3, hit_rate: float = 0.667) -> BacktestSummary:
    return BacktestSummary(
        n=n,
        scored=scored,
        hit_rate=hit_rate,
        indeterminate_rate=0.0,
        mean_delta=0.005,
        std_delta=0.012,
    )


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ── Validation ────────────────────────────────────────────────────────────


def test_rejects_unknown_model(client: TestClient):
    resp = client.get("/v1/backtest", params={"model": "not_a_model"})
    assert resp.status_code == 400
    assert "Unknown model" in resp.json()["detail"]


def test_rejects_unsupported_horizon(client: TestClient):
    resp = client.get(
        "/v1/backtest",
        params={"model": "moving_average_directional", "horizon": "42d"},
    )
    assert resp.status_code == 400
    assert "Unsupported horizon" in resp.json()["detail"]


def test_rejects_reversed_dates(client: TestClient):
    resp = client.get(
        "/v1/backtest",
        params={
            "model": "moving_average_directional",
            "from": "2026-05-10",
            "to": "2026-05-01",
        },
    )
    assert resp.status_code == 400
    assert "must be on or before" in resp.json()["detail"]


def test_rejects_unknown_symbol(client: TestClient):
    with patch(
        "apps.api.routers.backtest.instr_repo.get_by_symbol",
        new=AsyncMock(return_value=None),
    ):
        resp = client.get(
            "/v1/backtest",
            params={"model": "moving_average_directional", "symbol": "ZZZ"},
        )
    assert resp.status_code == 404
    assert "ZZZ" in resp.json()["detail"]


def test_rejects_retrain_days_out_of_range(client: TestClient):
    resp = client.get(
        "/v1/backtest",
        params={"model": "moving_average_directional", "retrain_days": 999},
    )
    assert resp.status_code == 422  # FastAPI's automatic Query bound check


# ── Happy path (mocked engine + persistence) ─────────────────────────────


def test_returns_config_summary_and_rows(client: TestClient):
    instrument = _fake_instrument()
    rows = [_sample_row(datetime(2026, 4, 1)), _sample_row(datetime(2026, 4, 2), outcome="miss")]
    summary = _sample_summary(n=2, scored=2, hit_rate=0.5)

    with patch(
        "apps.api.routers.backtest.instr_repo.get_by_symbol",
        new=AsyncMock(return_value=instrument),
    ), patch(
        "apps.api.routers.backtest.run_backtest",
        new=AsyncMock(return_value=(rows, summary)),
    ), patch(
        "apps.api.routers.backtest.persist_backtest_rows",
        new=AsyncMock(return_value=2),
    ):
        resp = client.get(
            "/v1/backtest",
            params={
                "model": "moving_average_directional",
                "from": "2026-04-01",
                "to": "2026-04-30",
                "horizon": "1d",
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["config"]["model"] == "moving_average_directional"
    assert body["config"]["from"] == "2026-04-01"
    assert body["config"]["to"] == "2026-04-30"
    assert body["config"]["persisted"] is True
    assert body["config"]["rows_inserted"] == 2
    assert body["summary"]["n"] == 2
    assert body["summary"]["scored"] == 2
    assert body["summary"]["hit_rate"] == 0.5
    assert len(body["rows"]) == 2
    assert body["rows"][0]["outcome"] == "hit"


def test_iso_format_on_generated_at(client: TestClient):
    instrument = _fake_instrument()
    rows = [_sample_row(datetime(2026, 4, 1, 12, 30))]
    with patch(
        "apps.api.routers.backtest.instr_repo.get_by_symbol",
        new=AsyncMock(return_value=instrument),
    ), patch(
        "apps.api.routers.backtest.run_backtest",
        new=AsyncMock(return_value=(rows, _sample_summary(n=1, scored=1))),
    ), patch(
        "apps.api.routers.backtest.persist_backtest_rows",
        new=AsyncMock(return_value=1),
    ):
        resp = client.get("/v1/backtest", params={"model": "moving_average_directional"})
    assert resp.status_code == 200
    ts = resp.json()["rows"][0]["generated_at"]
    assert ts.startswith("2026-04-01T12:30")


def test_persist_false_skips_persistence(client: TestClient):
    instrument = _fake_instrument()
    rows = [_sample_row(datetime(2026, 4, 1))]
    persist_mock = AsyncMock(return_value=1)
    with patch(
        "apps.api.routers.backtest.instr_repo.get_by_symbol",
        new=AsyncMock(return_value=instrument),
    ), patch(
        "apps.api.routers.backtest.run_backtest",
        new=AsyncMock(return_value=(rows, _sample_summary(n=1, scored=1))),
    ), patch(
        "apps.api.routers.backtest.persist_backtest_rows",
        new=persist_mock,
    ):
        resp = client.get(
            "/v1/backtest",
            params={"model": "moving_average_directional", "persist": "false"},
        )
    assert resp.status_code == 200
    assert resp.json()["config"]["persisted"] is False
    assert resp.json()["config"]["rows_inserted"] == 0
    persist_mock.assert_not_called()


def test_persist_skipped_when_no_rows(client: TestClient):
    """A backtest that produces zero rows (e.g. window too narrow for the
    55-close minimum) doesn't issue any DB writes."""
    instrument = _fake_instrument()
    persist_mock = AsyncMock(return_value=0)
    with patch(
        "apps.api.routers.backtest.instr_repo.get_by_symbol",
        new=AsyncMock(return_value=instrument),
    ), patch(
        "apps.api.routers.backtest.run_backtest",
        new=AsyncMock(return_value=([], _sample_summary(n=0, scored=0, hit_rate=0.0))),
    ), patch(
        "apps.api.routers.backtest.persist_backtest_rows",
        new=persist_mock,
    ):
        resp = client.get("/v1/backtest", params={"model": "moving_average_directional"})
    assert resp.status_code == 200
    assert resp.json()["config"]["rows_inserted"] == 0
    persist_mock.assert_not_called()


def test_default_window_is_90_days_back_from_to(client: TestClient):
    """No `from` param → from = to - 90 days."""
    instrument = _fake_instrument()
    with patch(
        "apps.api.routers.backtest.instr_repo.get_by_symbol",
        new=AsyncMock(return_value=instrument),
    ), patch(
        "apps.api.routers.backtest.run_backtest",
        new=AsyncMock(return_value=([], _sample_summary(n=0, scored=0))),
    ):
        resp = client.get(
            "/v1/backtest",
            params={"model": "moving_average_directional", "to": "2026-05-01"},
        )
    assert resp.status_code == 200
    body = resp.json()
    # 2026-05-01 minus 90 days = 2026-01-31.
    assert body["config"]["from"] == "2026-01-31"
    assert body["config"]["to"] == "2026-05-01"


def test_all_supported_models_accepted(client: TestClient):
    """Every model in SUPPORTED_MODELS passes validation; the engine call
    is mocked so we don't need real DB content."""
    instrument = _fake_instrument()
    for model in sorted(SUPPORTED_MODELS):
        with patch(
            "apps.api.routers.backtest.instr_repo.get_by_symbol",
            new=AsyncMock(return_value=instrument),
        ), patch(
            "apps.api.routers.backtest.run_backtest",
            new=AsyncMock(return_value=([], _sample_summary(n=0, scored=0))),
        ):
            resp = client.get("/v1/backtest", params={"model": model})
        assert resp.status_code == 200, f"model={model} failed: {resp.text}"
        assert resp.json()["config"]["model"] == model
