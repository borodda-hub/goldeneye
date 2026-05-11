"""Real EIA adapter stub."""
from apps.api.adapters._http import AdapterHTTPClient

EIA_BASE_URL = "https://api.eia.gov/v2/"
STORAGE_ROUTE = "natural-gas/stor/wkly/data/"

class EIAAdapter:
    """Real adapter — Phase roadmap. Reads from EIA APIv2."""
    async def get_storage_reports(self, limit: int = 100) -> list[dict]:
        raise NotImplementedError("real adapter — Phase roadmap")
    async def get_latest_storage(self) -> dict | None:
        raise NotImplementedError("real adapter — Phase roadmap")
