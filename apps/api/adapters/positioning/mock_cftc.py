"""Mock CFTC COT adapter. Serves from cot_generator output."""
import sys
from datetime import date
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

    async def get_cot_reports_range(self, start: date, end: date) -> list[dict]:
        """Protocol parity with the real adapter's Phase 31a range path."""
        return [r for r in _COT_REPORTS if start <= r["report_date"] <= end]
