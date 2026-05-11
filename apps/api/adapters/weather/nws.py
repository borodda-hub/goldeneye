"""Real NWS adapter stub."""
NWS_BASE_URL = "https://api.weather.gov/"
NWS_USER_AGENT = "NGTI-research-terminal contact@example.com"

class NWSAdapter:
    """Real adapter — Phase roadmap. Reads from NWS API."""
    async def get_observations(self, region: str, days: int = 60) -> list[dict]:
        raise NotImplementedError("real adapter — Phase roadmap")
    async def get_forecast(self, region: str) -> list[dict]:
        raise NotImplementedError("real adapter — Phase roadmap")
    async def get_national_hdd_anomaly(self) -> float:
        raise NotImplementedError("real adapter — Phase roadmap")
