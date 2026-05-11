"""Real news adapter stub."""
NEWSAPI_BASE = "https://newsapi.org/v2/"
EIA_TODAY_RSS = "https://www.eia.gov/todayinenergy/rss.xml"
NG_KEYWORDS = ["natural gas", "LNG", "Henry Hub", "EIA storage", "natgas", "Haynesville", "Appalachian gas", "Permian gas"]

class NewsAPIAdapter:
    """Real adapter — Phase roadmap. Reads from NewsAPI.org / GDELT."""
    async def get_recent_events(self, limit: int = 20) -> list[dict]:
        raise NotImplementedError("real adapter — Phase roadmap")
    async def get_events_by_category(self, category: str, limit: int = 10) -> list[dict]:
        raise NotImplementedError("real adapter — Phase roadmap")
