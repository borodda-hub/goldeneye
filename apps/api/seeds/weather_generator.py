"""
Generates daily weather observations and 14-day forecasts for 6 regions.
Observations: 60 days back from 2026-05-10 (2026-03-11 to 2026-05-10)
Forecasts: 14 days forward from 2026-05-10 (2026-05-11 to 2026-05-24)

Regions: northeast, midwest, mountain, pacific, south_central, southeast

Seasonal climatological normals (approximate May temperatures in °F):
  northeast: 58, midwest: 55, mountain: 50, pacific: 62, south_central: 75, southeast: 72

Algorithm (from docs/MOCK_DATA_SPEC.md):
- Daily temp_f = seasonal_mean(date, region) + anomaly
- anomaly[t] = 0.7 * anomaly[t-1] + epsilon, where epsilon ~ N(0, 6)
  (AR(1) persistence)
- Occasional "weather event": 3 per year → ~0.5 events in 60-day window
  A cold snap is -10 to -15°F for 5-10 days; a heat wave is +10 to +15°F
- HDD = max(0, 65 - temp_f)
- CDD = max(0, temp_f - 65)
- anomaly_f = temp_f - seasonal_mean(date, region)

Forecast:
- ts = forecast valid time, issued_at = 2026-05-10T12:00:00 (all forecasts issued same time)
- temp_f = observation[2026-05-10] + cumsum of random walk for each horizon day
  σ grows with horizon: σ_horizon = 1.5 * sqrt(horizon_days)
- horizon_days = 1 to 14
- HDD, CDD, anomaly_f computed from forecast temp_f

Return dict with two keys:
  {
    "observations": [{"ts": datetime, "region": str, "temp_f": float, "hdd": float,
                       "cdd": float, "precip_in": None, "anomaly_f": float, "source": "mock"}],
    "forecasts": [{"ts": datetime, "issued_at": datetime, "region": str, "horizon_days": int,
                   "temp_f": float, "hdd": float, "cdd": float, "anomaly_f": float, "source": "mock"}]
  }

Seasonal mean function: use a simple cosine model
  seasonal_mean(date, region) = base_temp[region] + amplitude * cos(2π * (doy - peak_doy) / 365)
  where amplitude ≈ 20°F, peak_doy ≈ 200 (mid-July)
"""
from __future__ import annotations

import math
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

# Ensure repo root is on sys.path when run as a script
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

REGIONS = ["northeast", "midwest", "mountain", "pacific", "south_central", "southeast"]

# Base temps (annual mean °F per region)
BASE_TEMPS = {
    "northeast":     53.0,
    "midwest":       50.0,
    "mountain":      46.0,
    "pacific":       58.0,
    "south_central": 68.0,
    "southeast":     65.0,
}

SEASONAL_AMPLITUDE = 20.0  # degrees F
PEAK_DOY = 200             # mid-July peak


def _seasonal_mean(d: date, region: str) -> float:
    """Seasonal climatological normal temperature for a given date and region."""
    doy = d.timetuple().tm_yday
    angle = 2 * math.pi * (doy - PEAK_DOY) / 365
    return BASE_TEMPS[region] + SEASONAL_AMPLITUDE * math.cos(angle)


def _hdd(temp_f: float) -> float:
    return max(0.0, 65.0 - temp_f)


def _cdd(temp_f: float) -> float:
    return max(0.0, temp_f - 65.0)


def generate() -> dict[str, list[dict[str, Any]]]:
    """Generate weather observations and forecasts deterministically."""
    rng = np.random.default_rng(42)

    today = date(2026, 5, 10)
    issued_at = datetime(2026, 5, 10, 12, 0, 0)

    # Build observation date range: 60 days ending today
    obs_dates = [today - timedelta(days=59 - i) for i in range(60)]
    assert obs_dates[0] == date(2026, 3, 12)
    assert obs_dates[-1] == today

    observations: list[dict[str, Any]] = []
    # Track final anomaly per region for forecast continuation
    last_anomaly: dict[str, float] = {}
    last_temp: dict[str, float] = {}

    for region in REGIONS:
        anomaly = 0.0  # start with no anomaly

        # Determine weather events for this region
        # ~0.5 events expected in 60-day window (3 per year / 365 * 60 ≈ 0.49)
        # Place 0 or 1 events randomly
        has_event = rng.random() < 0.5
        if has_event:
            event_start_idx = int(rng.integers(5, 50))
            event_duration  = int(rng.integers(5, 11))  # 5-10 days
            event_sign      = 1 if rng.random() > 0.5 else -1  # heat wave or cold snap
            event_magnitude = float(rng.uniform(10, 15)) * event_sign
        else:
            event_start_idx = -1
            event_duration  = 0
            event_magnitude = 0.0

        for i, d in enumerate(obs_dates):
            # AR(1) anomaly update
            epsilon = rng.normal(0, 6)
            anomaly = 0.7 * anomaly + epsilon

            # Apply weather event overlay
            if has_event and event_start_idx <= i < event_start_idx + event_duration:
                event_effect = event_magnitude * (1 - 0.1 * (i - event_start_idx))
            else:
                event_effect = 0.0

            s_mean = _seasonal_mean(d, region)
            temp_f = s_mean + anomaly + event_effect
            anomaly_f = temp_f - s_mean

            observations.append({
                "ts": datetime(d.year, d.month, d.day, 0, 0, 0),
                "region": region,
                "temp_f": round(temp_f, 2),
                "hdd": round(_hdd(temp_f), 2),
                "cdd": round(_cdd(temp_f), 2),
                "precip_in": None,
                "anomaly_f": round(anomaly_f, 2),
                "source": "mock",
            })

        last_anomaly[region] = anomaly
        last_temp[region] = temp_f  # type: ignore[possibly-undefined]

    # ── Forecasts ─────────────────────────────────────────────────────────────
    forecasts: list[dict[str, Any]] = []

    for region in REGIONS:
        base_temp = last_temp[region]

        for horizon in range(1, 15):  # 1 to 14
            forecast_date = today + timedelta(days=horizon)
            ts = datetime(forecast_date.year, forecast_date.month, forecast_date.day, 0, 0, 0)

            # σ grows with horizon
            sigma_h = 1.5 * math.sqrt(horizon)
            delta = rng.normal(0, sigma_h)
            temp_f = base_temp + delta

            s_mean = _seasonal_mean(forecast_date, region)
            anomaly_f = temp_f - s_mean

            forecasts.append({
                "ts": ts,
                "issued_at": issued_at,
                "region": region,
                "horizon_days": horizon,
                "temp_f": round(temp_f, 2),
                "hdd": round(_hdd(temp_f), 2),
                "cdd": round(_cdd(temp_f), 2),
                "anomaly_f": round(anomaly_f, 2),
                "source": "mock",
            })

    return {"observations": observations, "forecasts": forecasts}


if __name__ == "__main__":
    result = generate()
    obs = result["observations"]
    fcs = result["forecasts"]
    print(f"Observations: {len(obs)} (expected {60 * 6})")
    print(f"Forecasts: {len(fcs)} (expected {14 * 6})")
    print(f"First obs: {obs[0]}")
    print(f"First forecast: {fcs[0]}")
