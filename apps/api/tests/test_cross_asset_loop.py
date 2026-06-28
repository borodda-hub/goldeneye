"""Phase B5 — the cross-asset engine runs for index (ES) + rates (ZN) with no
commodity hardcode leaking.

Hermetic (no DB): drives the forecast engine + vol/range through the per-asset-class
config path on deterministic series at index/rates price scales, and asserts the
no-leak invariants the owner called out:
  - paper-engine tick value == the instrument's contract_size (ES 50 / ZN 1000), NOT
    the legacy 10000 (and commodity stays pinned to 10000 — issue #10).
  - the engine uses the CLASS config (regime bands, deadband), not the NG constants.
The DB-backed full loop (journal decision → auto-resolve → calibration) is exercised
live in the local verification (docs/PHASE_B5_PLAN.md §Verification).
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import numpy as np
import pytest

from apps.api.services import paper_engine
from apps.api.services.asset_config import config_for
from apps.api.services.ensemble import compute_ensemble
from apps.api.services.model_registry import ForecastContext, run_all
from apps.api.services.models.vol_range import predict as range_predict
from apps.api.services.models.volatility_regime import classify as classify_regime

# asset_class, contract_size, base_price, daily_vol, seed
CASES = [
    ("index", 50.0, 5000.0, 0.011, 101),   # ES — S&P 500
    ("rates", 1000.0, 110.0, 0.0035, 202),  # ZN — 10y Treasury
]


def _series(base: float, vol: float, seed: int) -> list[float]:
    rng = np.random.default_rng(seed)
    return [round(float(p), 6) for p in base * np.exp(np.cumsum(rng.standard_normal(140) * vol))]


@pytest.mark.parametrize("asset_class,contract_size,base,vol,seed", CASES)
async def test_full_engine_runs_no_crash(asset_class, contract_size, base, vol, seed):
    closes = _series(base, vol, seed)
    ctx = ForecastContext(symbol="X", closes=closes, asset_class=asset_class)

    results = await run_all(ctx)
    assert len(results) == 4  # full voter lineup, not the insufficient-data fallback
    ens = compute_ensemble(results)
    assert ens["direction"] in ("bullish", "bearish", "neutral")
    rng = range_predict(closes, "1w")
    assert rng is not None and rng.sigma_daily > 0  # vol/range produced a band


@pytest.mark.parametrize("asset_class,contract_size,base,vol,seed", CASES)
def test_uses_class_config_not_commodity(asset_class, contract_size, base, vol, seed):
    cfg = config_for(asset_class)
    commodity = config_for("commodity")
    # The class config is distinct from the NG baseline on the knobs B5 retunes.
    assert cfg.vol_regime_bands.normal != commodity.vol_regime_bands.normal
    assert cfg.default_deadband != commodity.default_deadband
    # ForecastContext resolves to this same config.
    ctx = ForecastContext(symbol="X", closes=_series(base, vol, seed), asset_class=asset_class)
    assert ctx.cfg is cfg
    # The regime classifier honours the class bands (no NG-band leak): a vol level
    # between the rates/index 'normal' cutoff and the much-higher commodity cutoff
    # classifies differently under the two band sets.
    cls_normal = cfg.vol_regime_bands.normal
    com_normal = commodity.vol_regime_bands.normal
    probe = cls_normal + (com_normal - cls_normal) / 2
    flat = [base * (1.0 + probe / (252**0.5) * (1 if i % 2 else -1)) for i in range(60)]
    assert classify_regime(flat, cfg) != classify_regime(flat, commodity)


@pytest.mark.parametrize("asset_class,contract_size,base,vol,seed", CASES)
async def test_tick_value_is_contract_size_not_10000(asset_class, contract_size, base, vol, seed):
    instr = SimpleNamespace(asset_class=asset_class, contract_size=contract_size)
    with patch.object(paper_engine.instr_repo, "get_by_id", AsyncMock(return_value=instr)):
        tv = await paper_engine._resolve_tick_value(AsyncMock(), None)
    assert tv == contract_size  # ES 50 / ZN 1000 — NOT the legacy 10000


async def test_existing_commodities_still_pinned_to_legacy_tick():
    """The deferral guard (#10): existing commodity/metal keep 10000 paper-MTM."""
    for ac, cs in [("commodity", 1000.0), ("metal", 100.0)]:
        instr = SimpleNamespace(asset_class=ac, contract_size=cs)
        with patch.object(paper_engine.instr_repo, "get_by_id", AsyncMock(return_value=instr)):
            tv = await paper_engine._resolve_tick_value(AsyncMock(), None)
        assert tv == 10_000.0  # pinned, not cs — demo continuity
