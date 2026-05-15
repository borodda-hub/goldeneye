"""Phase 16 — verify HO/RB/GC/SI instrument + contract chain seed loaded.

Same pattern as test_phase14_seed.py — reads the fixtures directly so we
exercise the same data the load_fixtures script writes, without DB roundtrip.
"""
from __future__ import annotations

import json
from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[3] / "packages" / "fixtures"

NEW_SYMBOLS = ["HO", "RB", "GC", "SI"]
EXPECTED_NAME = {
    "HO": "NY Harbor ULSD (Heating Oil)",
    "RB": "RBOB Gasoline",
    "GC": "Gold",
    "SI": "Silver",
}
EXPECTED_EXCHANGE = {
    "HO": "NYMEX",
    "RB": "NYMEX",
    "GC": "COMEX",
    "SI": "COMEX",
}


def _instruments() -> list[dict]:
    return json.loads((FIXTURES / "instruments.json").read_text())


def _contracts() -> list[dict]:
    return json.loads((FIXTURES / "contracts.json").read_text())


def test_instruments_fixture_includes_all_four():
    symbols = {r["symbol"] for r in _instruments()}
    assert {"NG", "CL", "HO", "RB", "GC", "SI"}.issubset(symbols)


def test_each_new_instrument_has_required_fields():
    rows = {r["symbol"]: r for r in _instruments()}
    for sym in NEW_SYMBOLS:
        r = rows[sym]
        assert r["name"] == EXPECTED_NAME[sym]
        assert r["exchange"] == EXPECTED_EXCHANGE[sym]
        assert r["currency"] == "USD"
        assert r["contract_size"] > 0
        assert r["tick_size"] > 0
        assert "yahoo_ticker" in r["metadata"]


def test_metals_marked_as_metal_asset_class():
    """GC and SI live on COMEX and are NOT classified as commodity."""
    rows = {r["symbol"]: r for r in _instruments()}
    assert rows["GC"]["asset_class"] == "metal"
    assert rows["SI"]["asset_class"] == "metal"
    # Energy quartet stays as commodity
    assert rows["HO"]["asset_class"] == "commodity"
    assert rows["RB"]["asset_class"] == "commodity"


def test_each_new_instrument_has_six_contracts():
    by_symbol: dict[str, int] = {}
    for r in _contracts():
        s = r["instrument_symbol"]
        by_symbol[s] = by_symbol.get(s, 0) + 1
    for sym in NEW_SYMBOLS:
        assert by_symbol.get(sym, 0) >= 6, (
            f"Instrument {sym} has {by_symbol.get(sym, 0)} contracts; expected ≥ 6"
        )


def test_each_new_instrument_has_exactly_one_front_month():
    front_by_symbol: dict[str, list[str]] = {}
    for r in _contracts():
        if r["is_front_month"]:
            front_by_symbol.setdefault(r["instrument_symbol"], []).append(
                r["contract_code"]
            )
    for sym in NEW_SYMBOLS:
        codes = front_by_symbol.get(sym, [])
        assert len(codes) == 1, f"{sym} has {len(codes)} front-month contracts: {codes}"


def test_contract_codes_follow_cme_convention():
    """All new contract codes are <prefix> + month letter + 2-digit year."""
    valid_letters = set("FGHJKMNQUVXZ")
    for r in _contracts():
        if r["instrument_symbol"] not in NEW_SYMBOLS:
            continue
        code = r["contract_code"]
        prefix_len = len(r["instrument_symbol"])
        assert len(code) == prefix_len + 3, f"Code {code} has unexpected length"
        assert code.startswith(r["instrument_symbol"])
        assert code[prefix_len] in valid_letters, f"Bad month letter in {code}"
        assert code[prefix_len + 1 :].isdigit(), f"Bad year digits in {code}"
