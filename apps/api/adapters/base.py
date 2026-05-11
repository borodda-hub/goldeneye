"""
Adapter protocols. All adapters (mock and real) implement these.
The app code only imports these protocols, never the concrete implementations.
"""
from typing import Protocol, runtime_checkable
from datetime import datetime, date


@runtime_checkable
class MarketDataAdapter(Protocol):
    async def get_bars(self, contract_code: str, resolution: str, from_dt: datetime, to_dt: datetime) -> list[dict]:
        """Returns list of OHLCV bar dicts: {ts, contract_code, resolution, open, high, low, close, volume, source}"""
    async def get_latest_price(self, contract_code: str) -> dict | None:
        """Returns the most recent bar dict or None."""
    async def get_curve_snapshot(self, symbol: str, as_of: datetime) -> list[dict]:
        """Returns [{contract_code, expiry, mid_price}] sorted by expiry."""


@runtime_checkable
class EnergyDataAdapter(Protocol):
    async def get_storage_reports(self, limit: int = 100) -> list[dict]:
        """Returns recent EIA storage report dicts, newest first."""
    async def get_latest_storage(self) -> dict | None:
        """Returns the most recent storage report dict or None."""


@runtime_checkable
class WeatherDataAdapter(Protocol):
    async def get_observations(self, region: str, days: int = 60) -> list[dict]:
        """Returns daily weather observation dicts for a region."""
    async def get_forecast(self, region: str) -> list[dict]:
        """Returns 14-day forecast dicts for a region, sorted by ts."""
    async def get_national_hdd_anomaly(self) -> float:
        """Returns population-weighted national 14-day HDD anomaly."""


@runtime_checkable
class PositioningDataAdapter(Protocol):
    async def get_cot_reports(self, limit: int = 52) -> list[dict]:
        """Returns recent COT report dicts, newest first."""
    async def get_latest_cot(self) -> dict | None:
        """Returns the most recent COT report dict or None."""


@runtime_checkable
class NewsDataAdapter(Protocol):
    async def get_recent_events(self, limit: int = 20) -> list[dict]:
        """Returns recent news event dicts, newest first."""
    async def get_events_by_category(self, category: str, limit: int = 10) -> list[dict]:
        """Returns events filtered by category."""
