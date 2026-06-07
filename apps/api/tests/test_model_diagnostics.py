"""Phase 26a — Model Diagnostics (bias / Brier decomposition / regime / drift).

Pure helpers are pinned directly; the DB aggregation is exercised with a mocked
session returning the grouped rows then the logreg feature rows.
"""
from __future__ import annotations

import uuid
from collections import namedtuple
from unittest.mock import AsyncMock, Mock

from apps.api.services.model_diagnostics import (
    DiagRow,
    _brier_decomposition,
    _directional_bias,
    _feature_drift,
    _regime_accuracy,
    compute_model_diagnostics,
)

# ── Brier (Murphy) decomposition ───────────────────────────────────────────


def test_brier_decomposition_matches_scalar_brier():
    """Single high-confidence bucket, 7 hits / 3 misses → must equal the 0.2125
    that services/model_calibration._brier produces for the same data."""
    rows = [
        DiagRow("bullish", "high", "normal", "hit", 7),
        DiagRow("bullish", "high", "normal", "miss", 3),
    ]
    d = _brier_decomposition(rows)
    # base = 0.7, single bucket → resolution = 0 (o_k == base).
    assert d["base_rate"] == 0.7
    assert d["resolution"] == 0.0
    assert d["reliability"] == 0.0025  # (0.75 - 0.70)^2
    assert d["uncertainty"] == 0.21  # 0.7 * 0.3
    assert d["brier"] == 0.2125
    assert d["n"] == 10


def test_brier_decomposition_resolution_rewards_discrimination():
    """A model whose high bucket really does beat its low bucket has resolution > 0."""
    rows = [
        DiagRow("bullish", "high", "normal", "hit", 9),
        DiagRow("bullish", "high", "normal", "miss", 1),  # high → 0.9
        DiagRow("bearish", "low", "normal", "hit", 1),
        DiagRow("bearish", "low", "normal", "miss", 9),  # low → 0.1
    ]
    d = _brier_decomposition(rows)
    assert d["resolution"] > 0.0  # the buckets discriminate


def test_brier_decomposition_empty():
    assert _brier_decomposition([])["brier"] is None


# ── Directional bias ───────────────────────────────────────────────────────


def test_directional_bias_one_sided_edge():
    rows = [
        DiagRow("bullish", "medium", "normal", "hit", 8),
        DiagRow("bullish", "medium", "normal", "miss", 2),  # bull → 0.8
        DiagRow("bearish", "medium", "normal", "hit", 2),
        DiagRow("bearish", "medium", "normal", "miss", 8),  # bear → 0.2
    ]
    b = _directional_bias(rows)
    assert b["bullish_calls"] == 10
    assert b["bearish_calls"] == 10
    assert b["call_skew"] == 0.5
    assert b["bullish_hit_rate"] == 0.8
    assert b["bearish_hit_rate"] == 0.2
    assert b["hit_rate_gap"] == 0.6  # only "works" long


# ── Regime-conditional accuracy ────────────────────────────────────────────


def test_regime_accuracy_splits_by_regime():
    rows = [
        DiagRow("bullish", "high", "normal", "hit", 8),
        DiagRow("bullish", "high", "normal", "miss", 2),
        DiagRow("bullish", "high", "crisis", "hit", 2),
        DiagRow("bullish", "high", "crisis", "miss", 8),
    ]
    r = _regime_accuracy(rows)
    assert r["normal"] == {"hit_rate": 0.8, "n": 10}
    assert r["crisis"] == {"hit_rate": 0.2, "n": 10}


def test_regime_accuracy_handles_null_regime():
    rows = [DiagRow("bullish", "low", None, "hit", 3)]
    assert _regime_accuracy(rows)["unknown"]["n"] == 3


# ── Feature-importance drift ───────────────────────────────────────────────


def test_feature_drift_detects_shift():
    early = ["momentum_5d"] * 8 + ["trend_vs_sma20"] * 2
    late = ["trend_vs_sma20"] * 8 + ["momentum_5d"] * 2
    d = _feature_drift(early, late)
    top_shift = d["shifts"][0]
    # both flip by 0.6 in magnitude; the largest-|delta| factor leads
    assert abs(top_shift["delta"]) == 0.6
    assert d["n_early"] == 10 and d["n_late"] == 10


def test_feature_drift_empty_halves():
    d = _feature_drift([], [])
    assert d["shifts"] == [] and d["early_top"] == []


# ── DB aggregation (mocked session) ────────────────────────────────────────

AggRow = namedtuple("AggRow", "model_name direction confidence vol_regime outcome n")
FeatRow = namedtuple("FeatRow", "generated_at supporting")


async def test_compute_model_diagnostics_assembles_cards():
    agg_rows = [
        AggRow("logreg_directional", "bullish", "high", "normal", "hit", 6),
        AggRow("logreg_directional", "bullish", "high", "normal", "miss", 4),
        AggRow("moving_average_directional", "bearish", "low", "crisis", "hit", 3),
        AggRow("moving_average_directional", "bearish", "low", "crisis", "miss", 7),
    ]
    feat_rows = [
        FeatRow(1, [{"factor": "momentum_5d", "weight": 0.4}]),
        FeatRow(2, [{"factor": "trend_vs_sma20", "weight": 0.3}]),
    ]
    agg_res = Mock()
    agg_res.all.return_value = agg_rows
    feat_res = Mock()
    feat_res.all.return_value = feat_rows
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[agg_res, feat_res])

    out = await compute_model_diagnostics(session, uuid.uuid4(), "1d")

    names = [m["name"] for m in out["models"]]
    assert names == ["logreg_directional", "moving_average_directional"]  # sorted
    logreg = out["models"][0]
    assert logreg["brier_decomposition"]["n"] == 10
    assert logreg["directional_bias"]["bullish_calls"] == 10
    assert "feature_drift" in logreg  # only logreg carries drift
    assert "feature_drift" not in out["models"][1]
    assert logreg["feature_drift"]["n_late"] >= 1
