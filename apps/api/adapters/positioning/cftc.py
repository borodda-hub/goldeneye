"""Real CFTC adapter stub."""
CFTC_BASE_URL = "https://publicreporting.cftc.gov/resource/"
DISAGGREGATED_RESOURCE = "kh3c-gbw2"
NG_MARKET_NAME = "NATURAL GAS - NEW YORK MERCANTILE EXCHANGE"

class CFTCAdapter:
    """Real adapter — Phase roadmap. Reads from CFTC PRE (Socrata)."""
    async def get_cot_reports(self, limit: int = 52) -> list[dict]:
        raise NotImplementedError("real adapter — Phase roadmap")
    async def get_latest_cot(self) -> dict | None:
        raise NotImplementedError("real adapter — Phase roadmap")
