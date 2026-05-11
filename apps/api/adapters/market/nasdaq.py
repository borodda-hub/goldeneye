"""Real market data adapter stub — Nasdaq Data Link / CME continuous contracts."""
from datetime import datetime
from apps.api.adapters._http import AdapterHTTPClient

NASDAQ_BASE_URL = "https://data.nasdaq.com/api/v3/datasets/CHRIS/"
NG_FRONT_SERIES = "CME_NG1"
NG_SECOND_SERIES = "CME_NG2"

class NasdaqMarketAdapter:
    """Real adapter — Phase roadmap. Reads from Nasdaq Data Link API."""

    async def get_bars(self, contract_code: str, resolution: str, from_dt: datetime, to_dt: datetime) -> list[dict]:
        raise NotImplementedError("real adapter — Phase roadmap")

    async def get_latest_price(self, contract_code: str) -> dict | None:
        raise NotImplementedError("real adapter — Phase roadmap")

    async def get_curve_snapshot(self, symbol: str, as_of: datetime) -> list[dict]:
        raise NotImplementedError("real adapter — Phase roadmap")
