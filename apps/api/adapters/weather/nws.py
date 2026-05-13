"""Real NWS weather adapter — gridded 7-day forecast via api.weather.gov.

NWS doesn't expose a clean per-region historical observation feed (observations
are per-station via /stations/{id}/observations). For the data the rest of
the stack actually consumes — forecasts and HDD anomaly — the gridded forecast
endpoint is the right source. `get_observations` returns an empty list on
the real path; consumers that need history continue to read from the
`weather_observations` table populated by other means.

Auth: none required. NWS asks for a descriptive User-Agent header.
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import date, datetime, timedelta
from typing import Any

from apps.api.adapters._http import AdapterHTTPClient
from apps.api.adapters.weather.regions import REGION_POINTS
from apps.api.seeds.weather_generator import _seasonal_mean

logger = logging.getLogger(__name__)

NWS_BASE_URL = "https://api.weather.gov/"
NWS_USER_AGENT = "Goldeneye-research-terminal contact@example.com"

# Population-weighted HDD aggregation across regions (matches mock).
HDD_POP_WEIGHTS: dict[str, float] = {
    "northeast": 0.25,
    "midwest": 0.22,
    "mountain": 0.08,
    "pacific": 0.12,
    "south_central": 0.18,
    "southeast": 0.15,
}

# Forecast cache TTL: 6 hours (cadence configured in data_health for weather.*).
_FORECAST_CACHE_TTL_SECONDS = 6 * 60 * 60
# Gridpoint metadata never changes — cache forever per process.


def _hdd(temp_f: float) -> float:
    return max(0.0, 65.0 - temp_f)


def _cdd(temp_f: float) -> float:
    return max(0.0, temp_f - 65.0)


def _to_fahrenheit(value: float, unit: str) -> float:
    if unit.upper() == "F":
        return float(value)
    return float(value) * 9.0 / 5.0 + 32.0


class NWSAdapter:
    """Real WeatherDataAdapter implementation using NWS gridded forecast."""

    def __init__(self) -> None:
        self._client = AdapterHTTPClient(adapter_name="weather.nws")
        self._gridpoint_cache: dict[tuple[float, float], str] = {}
        self._forecast_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}
        self._headers = {"User-Agent": NWS_USER_AGENT, "Accept": "application/geo+json"}

    async def get_observations(self, region: str, days: int = 60) -> list[dict[str, Any]]:
        # NWS doesn't have a clean per-region observation feed.
        # We log once so it's discoverable, then return empty.
        logger.debug("NWS adapter: get_observations is not implemented on real path")
        return []

    async def get_forecast(self, region: str) -> list[dict[str, Any]]:
        if region not in REGION_POINTS:
            return []
        now = time.time()
        cached = self._forecast_cache.get(region)
        if cached is not None and now - cached[0] < _FORECAST_CACHE_TTL_SECONDS:
            return cached[1]

        forecast = await self._fetch_region_forecast(region)
        self._forecast_cache[region] = (now, forecast)
        return forecast

    async def get_national_hdd_anomaly(self) -> float:
        """Population-weighted national HDD anomaly across all regions."""
        total = 0.0
        for region, weight in HDD_POP_WEIGHTS.items():
            fc = await self.get_forecast(region)
            if not fc:
                continue
            avg_anomaly = sum(f["anomaly_f"] for f in fc) / len(fc)
            hdd_anomaly = avg_anomaly * 0.8  # matches mock's HDD-weighted approximation
            total += hdd_anomaly * weight
        return total

    async def _fetch_region_forecast(self, region: str) -> list[dict[str, Any]]:
        """Pull per-point forecasts in parallel, then population-weight + aggregate."""
        points = REGION_POINTS[region]
        # Returns list[list[period_dict]] — one inner list per point.
        per_point: list[list[dict[str, Any]]] = await asyncio.gather(
            *(self._fetch_point_forecast(lat, lon) for lat, lon, _ in points),
            return_exceptions=False,
        )

        # Bucket periods into daily {date → list[(temp_f, weight)]}.
        daily: dict[date, list[tuple[float, float]]] = {}
        for periods, (_lat, _lon, weight) in zip(per_point, points):
            for period in periods:
                start = period.get("startTime")
                temp = period.get("temperature")
                unit = period.get("temperatureUnit") or "F"
                if start is None or temp is None:
                    continue
                try:
                    period_date = datetime.fromisoformat(start).date()
                except ValueError:
                    continue
                temp_f = _to_fahrenheit(temp, unit)
                daily.setdefault(period_date, []).append((temp_f, weight))

        issued_at = datetime.utcnow()
        today = issued_at.date()
        forecasts: list[dict[str, Any]] = []
        for forecast_date in sorted(daily.keys()):
            horizon = (forecast_date - today).days
            if horizon < 1:  # Skip "today" and any backfill the API returned.
                continue
            samples = daily[forecast_date]
            total_weight = sum(w for _, w in samples)
            if total_weight <= 0:
                continue
            # Mean of day/night × point weight.
            temp_f = sum(t * w for t, w in samples) / total_weight
            s_mean = _seasonal_mean(forecast_date, region)
            anomaly_f = temp_f - s_mean
            forecasts.append(
                {
                    "ts": datetime(
                        forecast_date.year, forecast_date.month, forecast_date.day
                    ),
                    "issued_at": issued_at,
                    "region": region,
                    "horizon_days": horizon,
                    "temp_f": round(temp_f, 2),
                    "hdd": round(_hdd(temp_f), 2),
                    "cdd": round(_cdd(temp_f), 2),
                    "anomaly_f": round(anomaly_f, 2),
                    "source": "nws",
                }
            )
        return forecasts

    async def _fetch_point_forecast(self, lat: float, lon: float) -> list[dict[str, Any]]:
        """Resolve gridpoint then fetch the 7-day forecast periods."""
        forecast_url = await self._resolve_gridpoint(lat, lon)
        response = await self._client.get(forecast_url, headers=self._headers)
        body = response.json()
        periods = body.get("properties", {}).get("periods", [])
        return periods if isinstance(periods, list) else []

    async def _resolve_gridpoint(self, lat: float, lon: float) -> str:
        key = (round(lat, 2), round(lon, 2))
        if key in self._gridpoint_cache:
            return self._gridpoint_cache[key]
        url = f"{NWS_BASE_URL}points/{lat},{lon}"
        response = await self._client.get(url, headers=self._headers)
        body = response.json()
        forecast_url = body.get("properties", {}).get("forecast")
        if not isinstance(forecast_url, str):
            raise RuntimeError(f"NWS /points returned no forecast URL for {lat},{lon}")
        self._gridpoint_cache[key] = forecast_url
        return forecast_url
