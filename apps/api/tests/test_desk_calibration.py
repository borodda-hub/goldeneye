"""Phase 7 — Desk Calibration Score (per-analyst skill-vs-luck)."""
from __future__ import annotations

from collections import namedtuple
from unittest.mock import AsyncMock, Mock

from apps.api.services.desk_calibration import compute_desk_calibration

# (user_id, thesis_conviction_at_write, confidence_pct, resolved_direction)
Row = namedtuple("Row", "user_id thesis_conviction_at_write confidence_pct resolved_direction")


def _rows(user_id, conviction, hits, misses, *, use_confidence=False):
    tconv = None if use_confidence else conviction
    conf = conviction if use_confidence else 50
    out = [Row(user_id, tconv, conf, "hit") for _ in range(hits)]
    out += [Row(user_id, tconv, conf, "miss") for _ in range(misses)]
    return out


async def _run(rows, *, min_resolved=10):
    res = Mock()
    res.all.return_value = rows
    session = AsyncMock()
    session.execute = AsyncMock(return_value=res)
    return await compute_desk_calibration(session, min_resolved=min_resolved)


async def test_well_calibrated_scores_better_than_overconfident():
    good = _rows("good", 60, hits=6, misses=4)  # 60% claimed, 60% actual
    over = _rows("over", 90, hits=4, misses=6)  # 90% claimed, 40% actual
    out = await _run(good + over)
    by = {a["user_id"]: a for a in out["analysts"]}

    assert by["good"]["brier"] == 0.24
    assert by["good"]["calibration_gap"] == 0.0
    assert by["over"]["brier"] == 0.49
    assert by["over"]["calibration_gap"] == 50.0  # overconfident
    # Best-calibrated ranks first.
    assert out["analysts"][0]["user_id"] == "good"


async def test_significance_gate_withholds_thin_records():
    thin = _rows("thin", 70, hits=2, misses=1)  # n=3 < 10
    out = await _run(thin)
    a = out["analysts"][0]
    assert a["n"] == 3
    assert a["qualifies"] is False
    # qualifying analysts always rank above non-qualifying ones
    fat = _rows("fat", 60, hits=6, misses=4)
    out2 = await _run(thin + fat)
    assert out2["analysts"][0]["user_id"] == "fat"
    assert out2["analysts"][0]["qualifies"] is True


async def test_conviction_falls_back_to_confidence_pct():
    rows = _rows("u", 80, hits=5, misses=5, use_confidence=True)
    out = await _run(rows, min_resolved=5)
    a = out["analysts"][0]
    assert a["mean_conviction"] == 80.0  # used confidence_pct, not the (null) snapshot
    assert a["hit_rate"] == 0.5


async def test_null_user_is_the_unattributed_desk():
    out = await _run(_rows(None, 50, hits=1, misses=1), min_resolved=1)
    assert out["analysts"][0]["user_id"] is None
