"""Unit tests for the data-health rollup service."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from apps.api.services.data_health import (
    DEFAULT_CADENCE_MIN,
    classify_status,
    expected_cadence_minutes,
    rollup_adapter_run,
)


@dataclass
class FakeRun:
    adapter_name: str
    status: str | None
    finished_at: datetime | None
    rows_ingested: int | None = 100
    error: str | None = None


def test_expected_cadence_market_short():
    assert expected_cadence_minutes("market.mock") == 5


def test_expected_cadence_eia_storage_weekly():
    assert expected_cadence_minutes("energy.eia.storage") == 7 * 24 * 60


def test_expected_cadence_cot_weekly():
    assert expected_cadence_minutes("positioning.cftc.cot") == 7 * 24 * 60


def test_expected_cadence_weather_6h():
    assert expected_cadence_minutes("weather.nws") == 6 * 60


def test_expected_cadence_unknown_uses_default():
    assert expected_cadence_minutes("custom.thing") == DEFAULT_CADENCE_MIN


def test_classify_ok_within_cadence():
    now = datetime(2026, 5, 10, 12, 0, 0)
    fin = now - timedelta(minutes=3)  # cadence 5; lag 3 → ok (within 1.5×=7.5)
    assert classify_status("market.mock", fin, "ok", now=now) == "ok"


def test_classify_degraded_between_1_5_and_3x():
    now = datetime(2026, 5, 10, 12, 0, 0)
    fin = now - timedelta(minutes=10)  # cadence 5; lag 10 → degraded (between 7.5 and 15)
    assert classify_status("market.mock", fin, "ok", now=now) == "degraded"


def test_classify_down_beyond_3x():
    now = datetime(2026, 5, 10, 12, 0, 0)
    fin = now - timedelta(minutes=20)  # cadence 5; lag 20 → down (> 15)
    assert classify_status("market.mock", fin, "ok", now=now) == "down"


def test_classify_down_when_last_status_is_error():
    now = datetime(2026, 5, 10, 12, 0, 0)
    fin = now - timedelta(minutes=1)
    assert classify_status("market.mock", fin, "error", now=now) == "down"


def test_classify_down_when_never_ran():
    assert classify_status("market.mock", None, None) == "down"


def test_rollup_envelope_shape():
    now = datetime(2026, 5, 10, 12, 0, 0)
    fin = now - timedelta(minutes=2)
    run = FakeRun(adapter_name="market.mock", status="ok", finished_at=fin)
    out = rollup_adapter_run(run, now=now)
    assert out["name"] == "market.mock"
    assert out["status"] == "ok"
    assert out["lag_minutes"] == 2.0
    assert out["expected_cadence_minutes"] == 5
    assert out["rows_ingested"] == 100
    assert out["error"] is None


def test_rollup_handles_no_finished_at():
    run = FakeRun(adapter_name="news.mock", status=None, finished_at=None)
    out = rollup_adapter_run(run)
    assert out["status"] == "down"
    assert out["last_success"] is None
    assert out["lag_minutes"] is None
