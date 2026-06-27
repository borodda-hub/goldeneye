"""Phase B5 — the byte-identical GOLDEN lock.

The critical honesty test for cross-asset portability: it proves the per-asset-class
config refactor changes **no existing behaviour**. On a fixed deterministic synthetic
close series, the full engine output for the DEFAULT (commodity) path — every voter's
ForecastResult, the ensemble dict, the vol-regime, and both vol_range bands — is frozen
into ``fixtures/b5_golden.json``.

Workflow: the baseline was captured on the UNREFACTORED engine (via the throwaway
``apps/api/_b5_golden_capture.py``, since deleted) and seen green BEFORE any refactor.
After the refactor, ``commodity`` (default), an explicit ``commodity`` config, and the
``metal`` fallback must all reproduce the frozen output byte-for-byte.

The voters are deterministic (no RNG — logreg inits weights to zeros), so the capture
is reproducible run-to-run; any drift is a real behaviour change and fails here.
"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import numpy as np
import pytest

from apps.api.services.ensemble import compute_ensemble
from apps.api.services.model_registry import ForecastContext, run_all
from apps.api.services.models.factor_composite import predict as factor_predict
from apps.api.services.models.holt_trend import predict as holt_predict
from apps.api.services.models.logreg_directional import predict as logreg_predict
from apps.api.services.models.moving_average_directional import predict as ma_predict
from apps.api.services.models.vol_range import predict as range_predict
from apps.api.services.models.volatility_regime import classify as classify_regime

GOLDEN_PATH = Path(__file__).resolve().parent / "fixtures" / "b5_golden.json"

# Fixed seed → a deterministic ~commodity-scale series. PCG64 is version-stable per
# numpy's stream-compatibility policy, so this reproduces across machines.
_SEED = 20260627
_N = 160
_BASE = 100.0
_DAILY_VOL = 0.018


def _series() -> list[float]:
    """A deterministic synthetic close series (no DB, no network, no wall-clock)."""
    rng = np.random.default_rng(_SEED)
    rets = rng.standard_normal(_N) * _DAILY_VOL
    prices = _BASE * np.exp(np.cumsum(rets))
    return [round(float(p), 6) for p in prices]


def _voters(closes: list[float]) -> list:
    """Mirror model_registry.run_all's call pattern (commodity / default path)."""
    regime = classify_regime(closes)
    results = [
        ma_predict(closes, "1d"),
        holt_predict(closes, "1d"),
        factor_predict(closes, "1d", latest_storage=None, latest_cot=None),
        logreg_predict(closes, "1d"),
    ]
    for r in results:
        r.vol_regime = regime
    return results


def build_golden() -> str:
    """Canonical JSON of the full engine output on the fixed series (default path).

    Used by the throwaway capture script to freeze the baseline, and by the test to
    re-derive and compare. Canonical (sorted keys, fixed indent) so equality is a true
    byte-for-byte check.
    """
    closes = _series()
    results = _voters(closes)
    payload = {
        "series_meta": {"n": len(closes), "first": closes[0], "last": closes[-1]},
        "regime": classify_regime(closes),
        "voters": [dataclasses.asdict(r) for r in results],
        "ensemble": compute_ensemble(results),
        "range_ewma": dataclasses.asdict(range_predict(closes, "1w", "ewma")),
        "range_har_log": dataclasses.asdict(range_predict(closes, "1w", "har_log")),
    }
    return json.dumps(payload, sort_keys=True, indent=2)


def test_golden_commodity_byte_identical():
    """The default (commodity) engine output equals the frozen baseline, byte-for-byte."""
    assert GOLDEN_PATH.exists(), (
        "b5_golden.json missing — capture the baseline first via _b5_golden_capture.py"
    )
    assert build_golden() == GOLDEN_PATH.read_text(encoding="utf-8")


def _registry_subset(voters: list, ensemble: dict) -> str:
    """Canonical JSON of just the registry-path output (voters + ensemble), the slice
    of the golden the per-asset-class config path is responsible for."""
    return json.dumps(
        {"voters": [dataclasses.asdict(r) for r in voters], "ensemble": ensemble},
        sort_keys=True,
        indent=2,
    )


@pytest.mark.parametrize("asset_class", ["commodity", "metal"])
async def test_golden_via_registry_commodity_and_metal(asset_class):
    """run_all → ensemble through the per-asset-class config path reproduces the frozen
    baseline for BOTH commodity (explicit) and metal (commodity fallback) — byte-for-byte.
    This is the cross-asset guarantee: the config refactor changed nothing for the
    existing demo's asset classes."""
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    expected_json = json.dumps(
        {"voters": golden["voters"], "ensemble": golden["ensemble"]},
        sort_keys=True,
        indent=2,
    )

    ctx = ForecastContext(symbol="X", closes=_series(), asset_class=asset_class)
    results = await run_all(ctx)
    actual_json = _registry_subset(results, compute_ensemble(results))

    assert actual_json == expected_json
