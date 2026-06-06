"""Mock news adapter. Serves from packages/fixtures/news_events.json."""
import json
import sys
from pathlib import Path
_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_FIXTURE_PATH = _REPO_ROOT / "packages" / "fixtures" / "news_events.json"
_EVENTS: list[dict] = sorted(
    json.loads(_FIXTURE_PATH.read_text(encoding="utf-8")),
    key=lambda e: e["published_at"],
    reverse=True,
)


class MockNewsAdapter:
    async def get_recent_events(self, limit: int = 20) -> list[dict]:
        return _EVENTS[:limit]

    async def get_events_by_category(self, category: str, limit: int = 10) -> list[dict]:
        return [e for e in _EVENTS if e.get("category") == category][:limit]
