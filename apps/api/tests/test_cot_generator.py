"""Phase 17 — COT seed generator parameterized per symbol.

Verifies per-symbol generation: right market code, categories sum to open
interest, managed-money net stays within the symbol's band, OI near the
symbol's baseline. NG remains the canonical 1.4M-OI market.
"""
from __future__ import annotations

import pytest

from apps.api.seeds.cot_generator import COT_PARAMS, generate


def test_params_cover_six_symbols():
    assert set(COT_PARAMS) == {"NG", "CL", "HO", "RB", "GC", "SI"}


@pytest.mark.parametrize("symbol", sorted(COT_PARAMS))
def test_generate_rows_for_each_symbol(symbol):
    params = COT_PARAMS[symbol]
    rows = generate(symbol)
    assert len(rows) == 100
    for r in rows:
        assert r["cftc_contract_market_code"] == params.cftc_contract_market_code
        assert r["contract_market_name"] == params.contract_market_name

        oi = r["open_interest_total"]
        long_sum = (
            r["producer_long"]
            + r["swap_long"]
            + r["managed_money_long"]
            + r["other_reportable_long"]
            + r["nonreportable_long"]
        )
        short_sum = (
            r["producer_short"]
            + r["swap_short"]
            + r["managed_money_short"]
            + r["other_reportable_short"]
            + r["nonreportable_short"]
        )
        assert long_sum == oi, f"{symbol} long categories must sum to OI"
        assert short_sum == oi, f"{symbol} short categories must sum to OI"

        # No negative category counts.
        assert min(
            r["producer_long"],
            r["producer_short"],
            r["swap_long"],
            r["swap_short"],
            r["managed_money_long"],
            r["managed_money_short"],
            r["nonreportable_long"],
            r["nonreportable_short"],
        ) >= 0

        # Managed-money net within the symbol's band (allow rounding slack).
        mm_net = r["managed_money_long"] - r["managed_money_short"]
        assert params.mm_net_min - 5_000 <= mm_net <= params.mm_net_max + 5_000


@pytest.mark.parametrize("symbol", sorted(COT_PARAMS))
def test_open_interest_near_baseline(symbol):
    params = COT_PARAMS[symbol]
    rows = generate(symbol)
    ois = [r["open_interest_total"] for r in rows]
    # Drift is ±10% + noise; stay within a generous band of the baseline.
    assert min(ois) >= params.oi_baseline * 0.5
    assert max(ois) <= params.oi_baseline * 1.3


def test_generate_is_deterministic():
    assert generate("NG") == generate("NG")


def test_each_symbol_has_distinct_market_code():
    codes = {sym: generate(sym)[0]["cftc_contract_market_code"] for sym in COT_PARAMS}
    assert len(set(codes.values())) == len(COT_PARAMS)
