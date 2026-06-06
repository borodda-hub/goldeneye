"""Phase 5 — Model Calibration Scorecard (reliability + Brier).

The Brier/reliability math is pinned directly; the aggregation is exercised with
a mocked session returning grouped (model, regime, confidence, outcome, n) rows.
"""
from __future__ import annotations

import uuid
from collections import namedtuple
from unittest.mock import AsyncMock, Mock

from apps.api.services.model_calibration import (
    CONFIDENCE_PROB,
    _brier,
    compute_model_calibration,
)

Row = namedtuple("Row", "model_name vol_regime confidence outcome n")


def test_brier_known_value():
    # high → claimed 0.75; 7 hits, 3 misses
    buckets = [{"claimed_prob": 0.75, "hits": 7, "misses": 3}]
    brier, n = _brier(buckets)
    # (7*(0.75-1)^2 + 3*0.75^2)/10 = (0.4375 + 1.6875)/10 = 0.2125
    assert brier == 0.2125
    assert n == 10


def test_brier_empty_is_none():
    assert _brier([]) == (None, 0)


async def _run(rows, *, by_regime=False):
    res = Mock()
    res.all.return_value = rows
    session = AsyncMock()
    session.execute = AsyncMock(return_value=res)
    return await compute_model_calibration(
        session, uuid.uuid4(), "1d", by_regime=by_regime
    )


async def test_scorecard_reliability_and_brier():
    rows = [
        Row("ma", "normal", "high", "hit", 7),
        Row("ma", "normal", "high", "miss", 3),
    ]
    out = await _run(rows)
    assert out["confidence_prob"] == CONFIDENCE_PROB
    m = out["models"][0]
    assert m["name"] == "ma"
    assert m["n"] == 10
    assert m["hit_rate"] == 0.7
    assert m["brier"] == 0.2125
    high = next(b for b in m["buckets"] if b["confidence"] == "high")
    assert high["claimed_prob"] == 0.75
    assert high["actual_rate"] == 0.7  # claimed 0.75 but actually 0.70 → overconfident


async def test_by_regime_splits_the_scorecard():
    rows = [
        Row("ma", "normal", "high", "hit", 8),
        Row("ma", "normal", "high", "miss", 2),  # normal: 0.8 actual
        Row("ma", "crisis", "high", "hit", 2),
        Row("ma", "crisis", "high", "miss", 8),  # crisis: 0.2 actual
    ]
    out = await _run(rows, by_regime=True)
    m = out["models"][0]
    assert m["n"] == 20
    assert m["hit_rate"] == 0.5  # blended
    regimes = m["by_regime"]
    assert regimes["normal"]["hit_rate"] == 0.8
    assert regimes["crisis"]["hit_rate"] == 0.2
    # crisis is worse-calibrated (claimed 0.75, actual 0.2) → higher Brier
    assert regimes["crisis"]["brier"] > regimes["normal"]["brier"]


async def test_unknown_confidence_maps_to_medium():
    rows = [Row("m", None, "bogus", "hit", 1), Row("m", None, "bogus", "miss", 1)]
    out = await _run(rows)
    b = out["models"][0]["buckets"][0]
    assert b["confidence"] == "medium"
    assert b["claimed_prob"] == CONFIDENCE_PROB["medium"]
