"""Phase 16 — Yahoo symbol mapping for energy + metals contracts.

The adapter routes contract codes to Yahoo via a prefix→exchange-suffix
table inside `apps.api.adapters.market.yahoo_delayed`. These tests lock
the table down for the six instruments NGTI ships today, and the
default-fallback behavior for an unknown prefix.
"""
from __future__ import annotations

from apps.api.adapters.market.yahoo_delayed import contract_to_yahoo_symbol


# ── energy: NYMEX ".NYM" suffix ─────────────────────────────────────────────


def test_ng_contract_routes_to_nymex():
    assert contract_to_yahoo_symbol("NGM26", "NG") == "NGM26.NYM"


def test_cl_contract_routes_to_nymex():
    assert contract_to_yahoo_symbol("CLN26", "CL") == "CLN26.NYM"


def test_ho_contract_routes_to_nymex():
    assert contract_to_yahoo_symbol("HOM26", "HO") == "HOM26.NYM"


def test_rb_contract_routes_to_nymex():
    assert contract_to_yahoo_symbol("RBM26", "RB") == "RBM26.NYM"


# ── metals: COMEX ".CMX" suffix ─────────────────────────────────────────────


def test_gc_contract_routes_to_comex():
    assert contract_to_yahoo_symbol("GCM26", "GC") == "GCM26.CMX"


def test_si_contract_routes_to_comex():
    assert contract_to_yahoo_symbol("SIN26", "SI") == "SIN26.CMX"


def test_hg_contract_routes_to_comex():
    """Copper isn't seeded yet but the mapping is in place for the follow-up."""
    assert contract_to_yahoo_symbol("HGN26", "HG") == "HGN26.CMX"


# ── continuous-front fallback ────────────────────────────────────────────────


def test_empty_contract_falls_back_to_continuous_front():
    assert contract_to_yahoo_symbol(None, "GC") == "GC=F"
    assert contract_to_yahoo_symbol("", "SI") == "SI=F"


def test_malformed_contract_falls_back_to_continuous_front():
    # Doesn't match the <prefix><month-letter><2-digit-year> pattern.
    assert contract_to_yahoo_symbol("WHATEVER", "NG") == "NG=F"


# ── unknown prefix defaults to NYMEX ─────────────────────────────────────────


def test_unknown_prefix_defaults_to_nymex():
    """When a contract uses a prefix not in the suffix table, default to .NYM.
    Yahoo returns an empty body for a wrong-listing request, so this surfaces
    upstream as quiet "no data" instead of a crash."""
    assert contract_to_yahoo_symbol("XYM26", "XY") == "XYM26.NYM"
