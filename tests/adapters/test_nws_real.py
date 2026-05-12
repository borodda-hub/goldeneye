"""Unit tests for the real NWS adapter — temp aggregation, weighting, caching."""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from apps.api.adapters.weather.nws import NWSAdapter, _to_fahrenheit


def _period(start: datetime, temp: int, unit: str = "F") -> dict:
    return {
        "startTime": start.isoformat(),
        "endTime": (start + timedelta(hours=12)).isoformat(),
        "temperature": temp,
        "temperatureUnit": unit,
    }


def _forecast_body(periods: list[dict]) -> dict:
    return {"properties": {"periods": periods}}


def _points_body(forecast_url: str = "https://api.weather.gov/gridpoints/OKX/33,35/forecast") -> dict:
    return {"properties": {"forecast": forecast_url, "gridId": "OKX", "gridX": 33, "gridY": 35}}


def test_to_fahrenheit_passthrough_when_F():
    assert _to_fahrenheit(72.0, "F") == 72.0


def test_to_fahrenheit_converts_celsius():
    assert _to_fahrenheit(0.0, "C") == 32.0
    assert _to_fahrenheit(100.0, "C") == 212.0


def test_get_observations_returns_empty_on_real_path():
    adapter = NWSAdapter()
    result = asyncio.run(adapter.get_observations("northeast", days=10))
    assert result == []


def test_get_forecast_unknown_region_returns_empty():
    adapter = NWSAdapter()
    result = asyncio.run(adapter.get_forecast("antarctica"))
    assert result == []


def test_get_forecast_aggregates_periods_into_daily():
    """Day + night for the same date collapse into one daily record."""
    adapter = NWSAdapter()
    tomorrow = (datetime.utcnow() + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
    next_day = tomorrow + timedelta(days=1)

    # Two periods on each forecast day — daytime + overnight.
    periods = [
        _period(tomorrow, 80),
        _period(tomorrow.replace(hour=22), 60),
        _period(next_day, 78),
        _period(next_day.replace(hour=22), 58),
    ]

    async def fake_get(url, **_kw):
        class _FakeResponse:
            def json(self):
                if url.endswith("/forecast"):
                    return _forecast_body(periods)
                return _points_body()
        return _FakeResponse()

    with patch.object(adapter._client, "get", new=AsyncMock(side_effect=fake_get)):
        result = asyncio.run(adapter.get_forecast("northeast"))

    # Three points in northeast, all returning the same two periods → same per-day mean.
    assert len(result) >= 2
    first = result[0]
    # Mean of day(80) + night(60) = 70.
    assert first["temp_f"] == 70.0
    assert first["region"] == "northeast"
    assert first["source"] == "nws"
    assert first["horizon_days"] >= 1


def test_get_forecast_population_weights_across_points():
    """Different points get different temps; result is weighted by point weight."""
    adapter = NWSAdapter()
    tomorrow = (datetime.utcnow() + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)

    call_count = {"n": 0}

    async def fake_get(url, **_kw):
        if "/points/" in url:
            class _PtResp:
                def json(self_inner):
                    call_count["n"] += 1
                    # Point N's forecast URL embeds the index so we can differentiate.
                    return _points_body(f"https://api.weather.gov/forecast/{call_count['n']}")
            return _PtResp()
        # Forecast endpoint — temperature varies by URL.
        if url.endswith("/1"):
            return _StubResp([_period(tomorrow, 60), _period(tomorrow.replace(hour=22), 60)])
        if url.endswith("/2"):
            return _StubResp([_period(tomorrow, 80), _period(tomorrow.replace(hour=22), 80)])
        return _StubResp([_period(tomorrow, 100), _period(tomorrow.replace(hour=22), 100)])

    class _StubResp:
        def __init__(self, periods):
            self.periods = periods
        def json(self):
            return _forecast_body(self.periods)

    with patch.object(adapter._client, "get", new=AsyncMock(side_effect=fake_get)):
        result = asyncio.run(adapter.get_forecast("northeast"))

    # Northeast weights: NYC=0.4, Boston=0.35, Philly=0.25.
    # Expected weighted temp = 60*0.4 + 80*0.35 + 100*0.25 = 24 + 28 + 25 = 77.
    assert result[0]["temp_f"] == pytest.approx(77.0, abs=0.01)


def test_gridpoint_cache_reuses_resolved_url():
    """Second call to the same lat/lon doesn't re-hit /points/."""
    adapter = NWSAdapter()
    tomorrow = (datetime.utcnow() + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)

    point_calls = {"n": 0}
    forecast_calls = {"n": 0}

    async def fake_get(url, **_kw):
        class _Resp:
            def __init__(self, body):
                self.body = body
            def json(self):
                return self.body
        if "/points/" in url:
            point_calls["n"] += 1
            return _Resp(_points_body())
        forecast_calls["n"] += 1
        return _Resp(_forecast_body([_period(tomorrow, 70), _period(tomorrow.replace(hour=22), 70)]))

    with patch.object(adapter._client, "get", new=AsyncMock(side_effect=fake_get)):
        # First call resolves and forecasts.
        asyncio.run(adapter.get_forecast("northeast"))
        first_points = point_calls["n"]
        # Bust the forecast TTL cache to force re-fetch of forecasts only.
        adapter._forecast_cache.clear()
        asyncio.run(adapter.get_forecast("northeast"))

    # 3 points in northeast: 3 /points/ calls on the first pass, 0 on the second.
    assert first_points == 3
    assert point_calls["n"] == 3


def test_forecast_cache_hits_avoid_second_round_trip():
    adapter = NWSAdapter()
    tomorrow = (datetime.utcnow() + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)

    async def fake_get(url, **_kw):
        class _Resp:
            def json(_self):
                if "/points/" in url:
                    return _points_body()
                return _forecast_body([_period(tomorrow, 70), _period(tomorrow.replace(hour=22), 70)])
        return _Resp()

    mock_get = AsyncMock(side_effect=fake_get)
    with patch.object(adapter._client, "get", new=mock_get):
        asyncio.run(adapter.get_forecast("northeast"))
        first_count = mock_get.await_count
        asyncio.run(adapter.get_forecast("northeast"))
        second_count = mock_get.await_count

    assert second_count == first_count, "second call should hit cache and make zero HTTP requests"
