"""Mock CFTC COT adapter. Serves from cot_generator output."""
import sys
from pathlib import Path
_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from apps.api.seeds.cot_generator import generate as _gen

_COT_REPORTS: list[dict] = sorted(_gen(), key=lambda r: r["report_date"], reverse=True)


class MockCFTCAdapter:
    async def get_cot_reports(self, limit: int = 52) -> list[dict]:
        return _COT_REPORTS[:limit]

    async def get_latest_cot(self) -> dict | None:
        return _COT_REPORTS[0] if _COT_REPORTS else None
