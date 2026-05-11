"""
Mock market data adapter. Serves OHLCV from price_generator output.
Caches generator output at module import time (seed=42, deterministic).
"""
import sys
from pathlib import Path
_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from datetime import datetime
from apps.api.seeds.price_generator import generate as _gen

_DATA = _gen()
_DAILY_BARS: list[dict] = [b for b in _DATA["bars"] if b["resolution"] == "1d"]
_MINUTE_BARS: list[dict] = [b for b in _DATA["bars"] if b["resolution"] == "1m"]
_SNAPSHOTS: list[dict] = _DATA["snapshots"]
# Index by ts for fast lookup
_DAILY_BY_CODE = {}
for b in _DAILY_BARS:
    _DAILY_BY_CODE.setdefault(b["contract_code"], []).append(b)
# Sort each list by ts
for code in _DAILY_BY_CODE:
    _DAILY_BY_CODE[code].sort(key=lambda x: x["ts"])


class MockMarketAdapter:
    async def get_bars(self, contract_code: str, resolution: str, from_dt: datetime, to_dt: datetime) -> list[dict]:
        if resolution == "1m":
            source = _MINUTE_BARS
        else:
            source = _DAILY_BARS
        return [
            b for b in source
            if b["contract_code"] == contract_code
            and from_dt <= b["ts"] <= to_dt
        ]

    async def get_latest_price(self, contract_code: str) -> dict | None:
        bars = _DAILY_BY_CODE.get(contract_code, [])
        return bars[-1] if bars else None

    async def get_curve_snapshot(self, symbol: str, as_of: datetime) -> list[dict]:
        # Find the snapshot closest to as_of
        snaps = [s for s in _SNAPSHOTS if s["ts"] <= as_of]
        if not snaps:
            snaps = _SNAPSHOTS
        snap = max(snaps, key=lambda s: s["ts"])
        return snap["curve"]
