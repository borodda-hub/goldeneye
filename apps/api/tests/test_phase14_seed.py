"""Phase 14 Step 1 — verify the CL instrument + contract seed loaded.

Reads the fixtures directly so we exercise the same data the
load_fixtures script writes, without round-tripping the DB. The full
fixture roundtrip is covered by the existing seed integration tests.
"""
from __future__ import annotations

import json
from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[3] / "packages" / "fixtures"


def test_instruments_fixture_includes_cl():
    rows = json.loads((FIXTURES / "instruments.json").read_text())
    symbols = {r["symbol"] for r in rows}
    assert {"NG", "CL"}.issubset(symbols)

    cl = next(r for r in rows if r["symbol"] == "CL")
    assert cl["name"] == "WTI Crude Oil"
    assert cl["exchange"] == "NYMEX"
    assert cl["unit"] == "barrel"
    assert cl["contract_size"] == 1000
    assert cl["tick_size"] == 0.01


def test_cl_metadata_carries_per_adapter_codes():
    rows = json.loads((FIXTURES / "instruments.json").read_text())
    cl = next(r for r in rows if r["symbol"] == "CL")
    meta = cl["metadata"]
    # These three are required by Phase 14.2 (Yahoo) and 14.3 (CFTC).
    assert meta["yahoo_ticker"] == "CL=F"
    assert meta["cftc_market_code"] == "067651"
    # Bloomberg ticker is informational but lets us cross-check.
    assert meta["bloomberg_ticker"].startswith("CL")


def test_ng_metadata_backfilled_with_adapter_codes():
    """Adding the new metadata fields shouldn't break NG."""
    rows = json.loads((FIXTURES / "instruments.json").read_text())
    ng = next(r for r in rows if r["symbol"] == "NG")
    meta = ng["metadata"]
    assert meta["yahoo_ticker"] == "NG=F"
    assert meta["cftc_market_code"] == "023651"


def test_contracts_fixture_includes_cl_chain():
    rows = json.loads((FIXTURES / "contracts.json").read_text())
    cl_rows = [r for r in rows if r["instrument_symbol"] == "CL"]
    assert len(cl_rows) >= 12, "Expected at least 12 CL monthly contracts"
    fronts = [r for r in cl_rows if r["is_front_month"]]
    assert len(fronts) == 1, "Exactly one CL contract should be is_front_month"
    assert fronts[0]["contract_code"] == "CLN26"


def test_each_instrument_has_at_most_one_front_month():
    """The unique partial index `one_active_thesis_per_instrument` doesn't
    cover contracts, but logical correctness requires it. Catch fixture
    drift before it hits the DB."""
    rows = json.loads((FIXTURES / "contracts.json").read_text())
    by_symbol: dict[str, int] = {}
    for r in rows:
        if r.get("is_front_month"):
            by_symbol[r["instrument_symbol"]] = by_symbol.get(r["instrument_symbol"], 0) + 1
    for symbol, n in by_symbol.items():
        assert n == 1, f"Instrument {symbol} has {n} front-month contracts; expected 1"


def test_cl_contract_codes_follow_cme_convention():
    """CL monthly codes are CL + month letter + 2-digit year."""
    rows = json.loads((FIXTURES / "contracts.json").read_text())
    cl_rows = [r for r in rows if r["instrument_symbol"] == "CL"]
    valid_letters = set("FGHJKMNQUVXZ")
    for r in cl_rows:
        code = r["contract_code"]
        assert len(code) == 5, f"CL contract code {code} has wrong length"
        assert code.startswith("CL")
        assert code[2] in valid_letters, f"Bad month letter in {code}"
        assert code[3:].isdigit(), f"Bad year digits in {code}"
