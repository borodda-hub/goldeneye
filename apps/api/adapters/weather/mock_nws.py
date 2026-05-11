"""Mock NWS weather adapter. Serves from weather_generator output."""
import sys
from pathlib import Path
_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from apps.api.seeds.weather_generator import generate as _gen

_DATA = _gen()
_OBS: list[dict] = _DATA["observations"]
_FORECASTS: list[dict] = _DATA["forecasts"]

REGIONS = ["northeast", "midwest", "mountain", "pacific", "south_central", "southeast"]
HDD_POP_WEIGHTS = {"northeast": 0.25, "midwest": 0.22, "mountain": 0.08, "pacific": 0.12, "south_central": 0.18, "southeast": 0.15}


class MockNWSAdapter:
    async def get_observations(self, region: str, days: int = 60) -> list[dict]:
        obs = [o for o in _OBS if o["region"] == region]
        obs.sort(key=lambda x: x["ts"], reverse=True)
        return obs[:days]

    async def get_forecast(self, region: str) -> list[dict]:
        fc = [f for f in _FORECASTS if f["region"] == region]
        fc.sort(key=lambda x: x["horizon_days"])
        return fc

    async def get_national_hdd_anomaly(self) -> float:
        """Population-weighted national 14-day HDD anomaly."""
        total = 0.0
        for region, weight in HDD_POP_WEIGHTS.items():
            fc = await self.get_forecast(region)
            if fc:
                avg_anomaly = sum(f["anomaly_f"] for f in fc) / len(fc)
                hdd_anomaly = avg_anomaly * 0.8  # HDD-weighted approximation
                total += hdd_anomaly * weight
        return total
