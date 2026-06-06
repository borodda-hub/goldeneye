"""Unit tests for the price-backfill service (services/price_backfill.py).

Pure row-shaping is tested directly; the DB flow is exercised with a mocked
session + market adapter so it stays hermetic (no Postgres, no network).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, Mock

from apps.api.services.price_backfill import (
    BACKFILL_SOURCE,
    _bars_to_rows,
    backfill_instrument,
)


def _bar(ts: datetime, *, o=1.0, h=2.0, lo=0.5, c=1.5, v=100):
    return {"ts": ts, "open": o, "high": h, "low": lo, "close": c, "volume": v}


# ── pure row shaping ──────────────────────────────────────────────────────


def test_bars_to_rows_shape_and_source():
    cid = uuid.uuid4()
    ts = datetime(2026, 1, 2)
    rows = _bars_to_rows(cid, [_bar(ts)], resolution="1d")
    assert len(rows) == 1
    r = rows[0]
    assert r["contract_id"] == cid
    assert r["resolution"] == "1d"
    assert r["ts"] == ts
    assert r["source"] == BACKFILL_SOURCE
    assert (r["open"], r["high"], r["low"], r["close"], r["volume"]) == (
        1.0,
        2.0,
        0.5,
        1.5,
        100,
    )


def test_bars_to_rows_volume_defaults_to_zero():
    rows = _bars_to_rows(
        uuid.uuid4(),
        [{"ts": datetime(2026, 1, 2), "open": 1, "high": 1, "low": 1, "close": 1}],
        resolution="1d",
    )
    assert rows[0]["volume"] == 0


# ── backfill flow (mocked session + market) ───────────────────────────────


def _result(*, scalar=None, all_rows=None, rowcount=0) -> Mock:
    r = Mock()
    r.scalar_one_or_none.return_value = scalar
    r.all.return_value = all_rows or []
    r.rowcount = rowcount
    return r


async def test_backfill_inserts_real_bars_tagged_source():
    instr_id, cid = uuid.uuid4(), uuid.uuid4()
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _result(scalar=instr_id),                 # instrument lookup
            _result(all_rows=[(cid, "NGM26")]),       # contracts
            _result(rowcount=2),                      # insert
        ]
    )
    market = AsyncMock()
    market.get_bars = AsyncMock(
        return_value=[_bar(datetime(2026, 1, 2)), _bar(datetime(2026, 1, 3))]
    )

    res = await backfill_instrument(session, market, "NG")

    assert res.bars_inserted == 2
    assert res.contracts_filled == 1
    assert res.mock_bars_removed == 0
    # fetched 1d bars for the right contract
    code, resolution = market.get_bars.await_args.args[0:2]
    assert code == "NGM26"
    assert resolution == "1d"


async def test_backfill_replace_mock_deletes_then_inserts():
    instr_id, cid = uuid.uuid4(), uuid.uuid4()
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _result(scalar=instr_id),             # instrument lookup
            _result(all_rows=[(cid, "NGM26")]),   # contracts
            _result(rowcount=5),                  # delete mock
            _result(rowcount=3),                  # insert real
        ]
    )
    market = AsyncMock()
    market.get_bars = AsyncMock(return_value=[_bar(datetime(2026, 1, 2))])

    res = await backfill_instrument(session, market, "NG", replace_mock=True)

    assert res.mock_bars_removed == 5
    assert res.bars_inserted == 3


async def test_backfill_missing_instrument_is_a_noop():
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[_result(scalar=None)])
    market = AsyncMock()
    market.get_bars = AsyncMock()

    res = await backfill_instrument(session, market, "ZZ")

    assert res.bars_inserted == 0
    assert res.note is not None
    market.get_bars.assert_not_awaited()


async def test_backfill_empty_fetch_skips_contract_without_deleting():
    instr_id, cid = uuid.uuid4(), uuid.uuid4()
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _result(scalar=instr_id),
            _result(all_rows=[(cid, "NGM26")]),
        ]
    )
    market = AsyncMock()
    market.get_bars = AsyncMock(return_value=[])  # network/empty

    res = await backfill_instrument(session, market, "NG", replace_mock=True)

    # No real bars → no delete, no insert (no data-loss on a failed fetch).
    assert res.bars_inserted == 0
    assert res.mock_bars_removed == 0
    assert session.execute.await_count == 2  # only the two reads
