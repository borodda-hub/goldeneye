"""Phase 7 — Desk Calibration Score (per-analyst skill-vs-luck).

The B2 verdict math (Wilson 95% CI vs 0.50) is unit-tested here; the *honesty
lock* — a real coin-flip desk resolving to ``luck`` end-to-end — lives in the
gated `tests/db` suite (`test_desk_skill_verdict_e2e.py`), not in these mocks.
"""
from __future__ import annotations

from collections import namedtuple
from unittest.mock import AsyncMock, Mock

import pytest

from apps.api.services.desk_calibration import (
    SKILL_BASELINE,
    compute_desk_calibration,
    skill_verdict,
    wilson_interval,
)

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


# ── B2: skill-vs-luck verdict (Wilson 95% CI vs 0.50) ──────────────────────────


def test_wilson_interval_known_values():
    """Pin the math against hand-computed bounds (catches a silent z/formula change)."""
    low, high = wilson_interval(8, 10)  # 80% on a thin sample
    assert low == pytest.approx(0.4901, abs=1e-3)
    assert high == pytest.approx(0.9433, abs=1e-3)
    # n == 0 → no information → the full interval.
    assert wilson_interval(0, 0) == (0.0, 1.0)


def test_verdict_skill_only_when_lower_bound_clears_chance():
    # 70/100: Wilson low ≈ 0.604 > 0.50 → skill.
    assert skill_verdict(70, 100) == "skill"
    assert wilson_interval(70, 100)[0] > SKILL_BASELINE
    # 8/10: 80% hit-rate but Wilson low ≈ 0.49 < 0.50 → a hot streak is NOT skill.
    assert skill_verdict(8, 10) == "luck"


def test_verdict_below_gate_is_insufficient():
    assert skill_verdict(6, 6) == "insufficient"  # n < 10, no CI claim


async def test_strong_desk_reads_skill_with_ci():
    out = await _run(_rows("strong", 60, hits=70, misses=30))
    a = next(x for x in out["analysts"] if x["user_id"] == "strong")
    assert a["verdict"] == "skill"
    assert a["wilson_low"] > 0.5
    assert a["wilson_high"] <= 1.0
    assert out["baseline"] == 0.5


async def test_coinflip_desk_reads_luck():
    # 50/50 over a large sample → CI straddles 0.50 → luck (mocked mirror of the
    # gated e2e honesty lock; the real-DB version is the authoritative regression).
    out = await _run(_rows("coin", 50, hits=50, misses=50))
    a = next(x for x in out["analysts"] if x["user_id"] == "coin")
    assert a["verdict"] == "luck"
    assert a["wilson_low"] < 0.5 < a["wilson_high"]


async def test_small_edge_does_not_get_crowned():
    # 6/10 = 60% but n=10 → CI straddles 0.50 → luck, not skill.
    out = await _run(_rows("smalledge", 60, hits=6, misses=4))
    a = next(x for x in out["analysts"] if x["user_id"] == "smalledge")
    assert a["verdict"] == "luck"


async def test_sub_gate_record_has_no_ci_and_is_insufficient():
    out = await _run(_rows("thin", 70, hits=2, misses=1))  # n=3 < 10
    a = out["analysts"][0]
    assert a["qualifies"] is False
    assert a["verdict"] == "insufficient"
    assert a["wilson_low"] is None and a["wilson_high"] is None
