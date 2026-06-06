"""Phase 3 — auto-resolution engine.

The resolution logic is exercised with in-memory decision rows + a patched price
lookup (hermetic — no DB, no network). End-to-end resolution against real prices
is verified separately; here we pin the scoring → resolved_direction mapping and
the pending/no-price guards.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

from apps.api.models.orm.journal import UserDecisionJournal
from apps.api.services import auto_resolution


def _decision(
    *,
    direction: str = "bullish",
    horizon: int = 14,
    threshold: float = 1.0,
    anchor: float = 100.0,
    created: datetime | None = None,
    resolved: str | None = None,
) -> UserDecisionJournal:
    e = UserDecisionJournal(
        id=uuid.uuid4(),
        instrument_id=uuid.uuid4(),
        hypothesis="h",
        evidence=[],
        confidence_pct=70,
        predicted_direction=direction,
        horizon_days=horizon,
        threshold_pct=threshold,
        anchor_price=anchor,
        resolved_direction=resolved,
    )
    e.created_at = created or datetime(2026, 1, 1)
    return e


async def _run(entries, realized_seq):
    """Run the engine with a mocked session + patched realized-price lookup."""
    res_obj = Mock()
    res_obj.scalars.return_value.all.return_value = entries
    session = AsyncMock()
    session.execute = AsyncMock(return_value=res_obj)
    with patch.object(
        auto_resolution, "_realized_close", new=AsyncMock(side_effect=realized_seq)
    ):
        return await auto_resolution.resolve_open_decisions(
            session, now=datetime(2026, 6, 6, tzinfo=UTC)
        )


async def test_resolves_hit_miss_and_neutral():
    hit = _decision(direction="bullish", threshold=1.0)  # +6% > 1% → hit
    miss = _decision(direction="bearish", threshold=1.0)  # +6% but bearish → miss
    band = _decision(direction="bullish", threshold=10.0)  # +6% < 10% → neutral
    # realized 106 vs anchor 100 = +6% for each (one lookup per past-horizon entry)
    result = await _run([hit, miss, band], [106.0, 106.0, 106.0])

    assert hit.resolved_direction == "hit"
    assert miss.resolved_direction == "miss"
    assert band.resolved_direction == "neutral"
    assert all(e.auto_resolved for e in (hit, miss, band))
    assert all(e.resolved_at is not None for e in (hit, miss, band))
    assert result.resolved == 3
    assert result.by_outcome == {"hit": 1, "miss": 1, "neutral": 1}


async def test_future_horizon_stays_pending():
    future = _decision(created=datetime(2026, 6, 1), horizon=90)  # target > now
    result = await _run([future], [])  # _realized_close never called
    assert future.resolved_direction is None
    assert not future.auto_resolved  # engine left it untouched
    assert result.still_pending == 1
    assert result.resolved == 0


async def test_missing_price_is_skipped_not_resolved():
    e = _decision()
    result = await _run([e], [None])  # no realized close available
    assert e.resolved_direction is None
    assert result.no_price == 1
    assert result.resolved == 0


async def test_zero_anchor_is_skipped():
    e = _decision(anchor=0.0)
    result = await _run([e], [106.0])
    assert e.resolved_direction is None
    assert result.no_price == 1


def test_auto_resolve_endpoint():
    from fastapi.testclient import TestClient

    from apps.api.services.auto_resolution import ResolveResult
    from apps.api.src.main import app

    fake = ResolveResult(resolved=2, still_pending=1, no_price=0, by_outcome={"hit": 2})
    with patch(
        "apps.api.routers.journal.resolve_open_decisions",
        new=AsyncMock(return_value=fake),
    ):
        resp = TestClient(app).post("/v1/journal/auto-resolve")
    assert resp.status_code == 200
    body = resp.json()
    assert body["resolved"] == 2
    assert body["still_pending"] == 1
    assert body["by_outcome"] == {"hit": 2}
