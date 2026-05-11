"""Mock EIA storage adapter. Serves from storage_generator output."""
import sys
from pathlib import Path
_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from apps.api.seeds.storage_generator import generate as _gen

_STORAGE_REPORTS: list[dict] = sorted(_gen(), key=lambda r: r["report_date"], reverse=True)


class MockEIAAdapter:
    async def get_storage_reports(self, limit: int = 100) -> list[dict]:
        return _STORAGE_REPORTS[:limit]

    async def get_latest_storage(self) -> dict | None:
        return _STORAGE_REPORTS[0] if _STORAGE_REPORTS else None
