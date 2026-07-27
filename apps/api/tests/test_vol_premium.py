"""Phase D1b — shared vol-premium machinery (hermetic, synthetic data).

The load-bearing property: `analyze_pair` is the SINGLE implementation both
the D1 probe and the live surface use, and its live SHIP GATE gates what
the card may render. These tests pin the mechanics (shapes, bounds, gate
boundary, walk-forward bucketing) on deterministic synthetic series — the
real-data verdicts live in the probe + `docs/PHASE_D1_PLAN.md`.
"""
from __future__ import annotations

import asyncio
from datetime import date, timedelta

import numpy as np
import pytest

from apps.api.services.vol_premium import (
    PAIR_FOR_SYMBOL,
    TIMING_TESTED,
    analyze_pair,
    analyze_symbol,
)


def _business_days(start: date, n: int) -> list[date]:
    out, d = [], start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def _synthetic_pair(n_days: int = 1400, premium: float = 0.05):
    """Underlying with clustered vol + an IV index = future-ish vol + premium.
    Deterministic; enough Fridays past warm-up for a full analysis."""
    rng = np.random.default_rng(7)
    days = _business_days(date(2020, 1, 6), n_days)
    vol = 0.20 + 0.10 * np.sin(np.arange(n_days) / 90.0)  # slow vol cycle
    rets = rng.normal(0, vol / np.sqrt(252.0), n_days)
    closes = 50.0 * np.exp(np.cumsum(rets))
    iv = (vol + premium + rng.normal(0, 0.01, n_days)) * 100.0  # index points
    und = {d.isoformat(): float(c) for d, c in zip(days, closes)}
    ivs = {d.isoformat(): float(v) for d, v in zip(days, iv)}
    return und, ivs


def test_analyze_pair_shapes_and_bounds():
    und, ivs = _synthetic_pair()
    r = analyze_pair(und, ivs, "ewma")
    assert r is not None
    assert r["n"] >= 100
    assert r["n_eff"] == round(r["n"] / 4.2)
    # The constructed premium must replicate (sanity of the harness itself).
    assert r["g0_mean_prem"] > 0
    assert 0.0 <= r["g0_share"] <= 1.0
    cur = r["current"]
    assert cur is not None
    assert 0.0 <= cur["percentile"] <= 100.0
    assert cur["bucket"] in ("low", "mid", "high")
    assert cur["spread"] == pytest.approx(cur["sigma_f"] - cur["iv"])
    for name in ("low", "mid", "high"):
        t = r["terciles"][name]
        if t is not None:
            assert t.n >= 20 and t.se > 0


def test_ship_gate_boundary_semantics():
    """Ship gate = 'not WORSE than the market's own forecast' (delta < +1 SE)
    — strictly weaker than G1 ('BEATS by 1 SE'), by design."""
    und, ivs = _synthetic_pair()
    r = analyze_pair(und, ivs, "ewma")
    assert r is not None
    # Consistency: if G1 passes, the ship gate necessarily passes.
    if r["g1_passes"]:
        assert r["ship_gate"]
    # And the definitions are what the plan pre-registered.
    assert r["ship_gate"] == (r["g1_delta"] < r["g1_se"])
    assert r["g1_passes"] == (r["g1_delta"] < -r["g1_se"])


def test_thin_history_returns_none():
    und, ivs = _synthetic_pair(n_days=200)
    assert analyze_pair(und, ivs, "ewma") is None


def test_unsupported_symbol_is_none_without_network():
    """NG has no free implied-vol index — analyze_symbol must return None
    BEFORE any fetch (hermetic by construction)."""
    assert asyncio.run(analyze_symbol("NG")) is None
    assert asyncio.run(analyze_symbol("ZZ")) is None


def test_pair_registry_and_timing_verdicts_consistent():
    for _sym, (und_t, _iv_t) in PAIR_FOR_SYMBOL.items():
        assert und_t in TIMING_TESTED, f"{und_t} missing a D1 timing verdict"
    # The D1 record: crude + equities passed, gold failed (PHASE_D1_PLAN §revisit).
    assert TIMING_TESTED == {"USO": True, "SPY": True, "GLD": False}
