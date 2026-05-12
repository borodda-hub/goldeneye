"""Unit tests for the example journal + paper-trade seed data builder.

Validates the pure-data layer (row builders, PnL math, journal-ref linkage)
without hitting Postgres. The end-to-end seed against the test container
is exercised when `apps.api.seeds.demo` is run.
"""
from __future__ import annotations

import uuid

from apps.api.seeds.example_journal_and_trades import (
    NG_TICK_VALUE_USD,
    _example_journal_rows,
    _example_paper_trade_rows,
)


def test_journal_rows_has_three_entries_with_required_fields():
    instr = uuid.uuid4()
    rows = _example_journal_rows(instr)
    assert len(rows) == 3
    for r in rows:
        assert r["instrument_id"] == instr
        assert isinstance(r["hypothesis"], str) and r["hypothesis"]
        assert 0 <= r["confidence_pct"] <= 100
        assert isinstance(r["evidence"], list) and len(r["evidence"]) >= 1
        assert isinstance(r["llm_review"], dict)
        assert "text" in r["llm_review"]
        assert "safety" in r["llm_review"]


def test_journal_llm_reviews_avoid_forbidden_phrases():
    """Pre-generated reviews must clear the safety scan."""
    from apps.api.services.safety import scan_for_forbidden

    for row in _example_journal_rows(uuid.uuid4()):
        review_text = row["llm_review"]["text"]
        matches = scan_for_forbidden(review_text)
        assert not matches, f"forbidden phrase in seeded review: {matches!r}\n{review_text!r}"


def test_paper_trade_pnl_long_win():
    instr, contract = uuid.uuid4(), uuid.uuid4()
    journal_ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
    rows = _example_paper_trade_rows(instr, contract, journal_ids)

    win = rows[0]
    assert win["side"] == "long"
    assert win["status"] == "closed"
    # Long: (exit - entry) × size × 10_000.
    expected = round((win["exit_price"] - win["entry_price"]) * win["size_contracts"] * NG_TICK_VALUE_USD, 2)
    assert win["outcome_pnl"] == expected
    assert win["outcome_pnl"] > 0


def test_paper_trade_pnl_short_loss():
    instr, contract = uuid.uuid4(), uuid.uuid4()
    journal_ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
    rows = _example_paper_trade_rows(instr, contract, journal_ids)

    loss = rows[1]
    assert loss["side"] == "short"
    assert loss["status"] == "closed"
    # Short: -(exit - entry) × size × 10_000 — losing short means exit > entry.
    expected = round(-1 * (loss["exit_price"] - loss["entry_price"]) * loss["size_contracts"] * NG_TICK_VALUE_USD, 2)
    assert loss["outcome_pnl"] == expected
    assert loss["outcome_pnl"] < 0


def test_paper_trade_open_position_has_no_pnl():
    instr, contract = uuid.uuid4(), uuid.uuid4()
    journal_ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
    rows = _example_paper_trade_rows(instr, contract, journal_ids)

    open_trade = rows[2]
    assert open_trade["status"] == "open"
    assert open_trade["closed_at"] is None
    assert open_trade["exit_price"] is None
    assert open_trade["outcome_pnl"] is None


def test_paper_trades_link_to_journal_entries_by_index():
    instr, contract = uuid.uuid4(), uuid.uuid4()
    j_ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
    rows = _example_paper_trade_rows(instr, contract, j_ids)
    assert [r["journal_ref"] for r in rows] == j_ids


def test_paper_trades_handle_missing_journal_ids():
    """Trade builder must tolerate fewer journal_ids than trades."""
    instr, contract = uuid.uuid4(), uuid.uuid4()
    rows = _example_paper_trade_rows(instr, contract, [])
    assert all(r["journal_ref"] is None for r in rows)


def test_paper_trades_handle_no_bound_contract():
    """contract_id is nullable; trades should still build cleanly."""
    instr = uuid.uuid4()
    j_ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
    rows = _example_paper_trade_rows(instr, None, j_ids)
    assert all(r["contract_id"] is None for r in rows)
    assert all(r["instrument_id"] == instr for r in rows)
