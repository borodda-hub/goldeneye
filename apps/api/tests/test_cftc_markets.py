"""Phase 17 — CFTC MARKETS extended to the thin-tier quartet.

Construction-only tests (no network): every symbol builds a CFTCAdapter and
carries the expected market code; unknown symbols still raise ValueError.
"""
from __future__ import annotations

import pytest

from apps.api.adapters.positioning.cftc import MARKETS, CFTCAdapter

EXPECTED_CODES = {
    "NG": "023651",
    "CL": "067651",
    "HO": "022651",
    "RB": "111659",
    "GC": "088691",
    "SI": "084691",
}


def test_markets_has_all_six_symbols():
    assert set(MARKETS) >= set(EXPECTED_CODES)


@pytest.mark.parametrize("symbol", sorted(EXPECTED_CODES))
def test_adapter_builds_per_symbol(symbol):
    adapter = CFTCAdapter(symbol)
    assert adapter._market.contract_code == EXPECTED_CODES[symbol]


def test_market_codes_match_table():
    for sym, code in EXPECTED_CODES.items():
        assert MARKETS[sym].contract_code == code


def test_unknown_symbol_raises():
    with pytest.raises(ValueError):
        CFTCAdapter("ZZZ")
