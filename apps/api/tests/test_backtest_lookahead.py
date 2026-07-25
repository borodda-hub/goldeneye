"""Phase 10 Step 2 — look-ahead safety tests.

The credibility-load-bearing piece. Two layers of defense:

1. PROPERTY TESTS on the chokepoint helpers (_closes_as_of, _storage_as_of,
   _cot_as_of, _context_as_of). For a given as_of, the helpers must:
     - never return a price bar with ts >= as_of
     - never return a storage report with report_date > as_of.date()
     - never return a COT report with release_date > as_of.date()
   We verify this by mocking the SQLAlchemy session and inspecting the
   compiled WHERE clauses + asserting on the returned values.

2. CHEATING-MODEL PROOF. A synthetic predict_fn that, IF the future were
   leaking into ctx.closes, would score 100% hit-rate on a controlled
   price series. With the chokepoint correctly enforced, the cheating
   model's hit-rate is bounded by chance. We run a full backtest against
   a FakeSession with a known price series and assert hit_rate <= 0.65,
   well below the 100% a true look-ahead would produce.
"""
from __future__ import annotations

import asyncio
import math
import re
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

import pytest

from apps.api.services.backtest import (
    BacktestConfig,
    _closes_as_of,
    _context_as_of,
    _cot_as_of,
    _eod,
    _storage_as_of,
    run_backtest,
)
from apps.api.services.models.moving_average_directional import ForecastResult

# ── Fake DB session ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class _Bar:
    ts: datetime
    close: float


@dataclass(frozen=True)
class _Storage:
    report_date: date
    surprise_bcf: float | None
    net_change_bcf: float | None
    # Needed by the seasonal-norm proxy (31a.0); None → proxy returns None.
    week_ending: date | None = None


@dataclass(frozen=True)
class _Cot:
    release_date: date
    managed_money_net: int | None
    # 31a.0: _cot_as_of filters by market; default = the NG contract code.
    cftc_contract_market_code: str = "023651"


class _FakeResult:
    """Mimic a SQLAlchemy Result for our two access patterns."""

    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def scalar_one_or_none(self) -> Any:
        return self._rows[0] if self._rows else None

    def scalars(self) -> _FakeScalars:
        return _FakeScalars(self._rows)

    def all(self) -> list[Any]:
        return list(self._rows)


class _FakeScalars:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def all(self) -> list[Any]:
        return list(self._rows)


class FakeSession:
    """In-memory session that answers based on a small handler table.

    Each call to execute() routes the Select to one of three loaders
    (prices / storage / cot) based on which model class appears in the
    compiled SQL. The handler also captures every call for assertions.
    """

    def __init__(
        self,
        *,
        bars: list[_Bar] | None = None,
        storage_reports: list[_Storage] | None = None,
        cot_reports: list[_Cot] | None = None,
    ) -> None:
        self.bars = sorted(bars or [], key=lambda b: b.ts)
        self.storage_reports = sorted(
            storage_reports or [], key=lambda r: r.report_date
        )
        self.cot_reports = sorted(
            cot_reports or [], key=lambda r: r.release_date
        )
        self.execute_calls: list[Any] = []

    async def execute(self, stmt: Any) -> _FakeResult:
        self.execute_calls.append(stmt)
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True})).lower()
        if "price_bars" in sql:
            return self._answer_prices(stmt, sql)
        if "eia_storage_reports" in sql:
            return self._answer_storage(stmt, sql)
        if "cot_reports" in sql:
            return self._answer_cot(stmt, sql)
        # Default — empty rows for any unknown table.
        return _FakeResult([])

    # ─── price-bar matcher ───
    def _answer_prices(self, stmt: Any, sql: str) -> _FakeResult:
        # Distinguish between the two select shapes the engine uses:
        #   select(PriceBar.ts, PriceBar.close) → tuples (closes-as-of)
        #   select(PriceBar.close)              → scalars (strict-before / on-or-after)
        wants_tuple = "price_bars.ts," in sql or "price_bars.ts ," in sql

        # Two WHERE shapes appear:
        #   ts < $as_of           (strict-before bound)
        #   ts >= $a AND ts <= $b (forward-window for end_close lookup)
        if "ts >=" in sql and "ts <=" in sql:
            start = _extract_datetime_after(sql, "ts >=")
            end = _extract_datetime_after(sql, "ts <=")
            if start is None or end is None:
                return _FakeResult([])
            matches = [b for b in self.bars if start <= b.ts <= end]
            matches.sort(key=lambda b: b.ts)
        else:
            as_of = _extract_datetime_after(sql, "ts <")
            if as_of is None:
                return _FakeResult([])
            matches = [b for b in self.bars if b.ts < as_of]
            matches.sort(key=lambda b: b.ts, reverse=True)

        limit = _extract_limit(sql) or 100
        matches = matches[:limit]
        if wants_tuple:
            return _FakeResult([(b.ts, b.close) for b in matches])
        return _FakeResult([b.close for b in matches])

    # ─── storage matcher ───
    def _answer_storage(self, stmt: Any, sql: str) -> _FakeResult:
        as_of_date = _extract_date_after(sql, "report_date <=")
        if as_of_date is None:
            return _FakeResult([])
        matches = [r for r in self.storage_reports if r.report_date <= as_of_date]
        matches.sort(key=lambda r: r.report_date, reverse=True)
        limit = _extract_limit(sql) or 1
        return _FakeResult(matches[:limit])

    # ─── cot matcher ───
    def _answer_cot(self, stmt: Any, sql: str) -> _FakeResult:
        as_of_date = _extract_date_after(sql, "release_date <=")
        if as_of_date is None:
            return _FakeResult([])
        matches = [r for r in self.cot_reports if r.release_date <= as_of_date]
        # Honor the 31a.0 market filter WHEN the statement carries it. When
        # the clause is absent (a regression to the symbol-blind query), the
        # fake returns the global rows — which is exactly what makes
        # test_cot_as_of_filters_by_market_code fail-without/pass-with.
        market_code = _extract_market_code(sql)
        if market_code is not None:
            matches = [
                r for r in matches if r.cftc_contract_market_code == market_code
            ]
        matches.sort(key=lambda r: r.release_date, reverse=True)
        return _FakeResult(matches[:2])


# Tiny SQL-string extractors. Not robust against arbitrary SQL, but
# adequate for the tightly-shaped statements our chokepoint helpers
# produce.
_TS_RE = re.compile(
    r"'(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?)'"
)
_DATE_RE = re.compile(r"'(\d{4}-\d{2}-\d{2})'")
_LIMIT_RE = re.compile(r"limit\s+(\d+)")


def _extract_datetime_after(sql: str, marker: str) -> datetime | None:
    idx = sql.find(marker)
    if idx < 0:
        return None
    tail = sql[idx:]
    m = _TS_RE.search(tail)
    if not m:
        return None
    raw = m.group(1).replace("T", " ")
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _extract_date_after(sql: str, marker: str) -> date | None:
    idx = sql.find(marker)
    if idx < 0:
        return None
    tail = sql[idx:]
    m = _DATE_RE.search(tail)
    if not m:
        return None
    try:
        return date.fromisoformat(m.group(1))
    except ValueError:
        return None


def _extract_limit(sql: str) -> int | None:
    m = _LIMIT_RE.search(sql)
    return int(m.group(1)) if m else None


_MARKET_CODE_RE = re.compile(r"cftc_contract_market_code\s*=\s*'([^']+)'")


def _extract_market_code(sql: str) -> str | None:
    m = _MARKET_CODE_RE.search(sql)
    return m.group(1) if m else None


# ── Property tests on _closes_as_of ───────────────────────────────────────


def _bars_from(start: date, n: int, base_price: float = 3.0) -> list[_Bar]:
    """A synthetic NG price series: deterministic mild sine wave."""
    return [
        _Bar(
            ts=datetime.combine(start + timedelta(days=i), datetime.min.time()),
            close=base_price + 0.5 * math.sin(i / 7.0) + 0.01 * i,
        )
        for i in range(n)
    ]


def test_closes_as_of_returns_only_past_bars():
    session = FakeSession(bars=_bars_from(date(2026, 2, 1), 90))
    as_of = _eod(date(2026, 4, 1))
    closes = asyncio.run(_closes_as_of(session, uuid.uuid4(), as_of, n=200))
    # Every returned close must correspond to a ts < as_of. Since FakeSession
    # already filtered on the SQL <, and the helper double-checks at the
    # Python level, this just verifies the count is what we expect.
    expected_count = sum(1 for b in session.bars if b.ts < as_of)
    assert len(closes) == expected_count


def test_closes_as_of_uses_strict_less_than_in_sql():
    """Direct SQL inspection: the WHERE clause must use < and not <=."""

    session = FakeSession(bars=[])
    as_of = _eod(date(2026, 4, 1))
    asyncio.run(_closes_as_of(session, uuid.uuid4(), as_of))
    assert len(session.execute_calls) == 1
    sql = str(
        session.execute_calls[0].compile(compile_kwargs={"literal_binds": True})
    ).lower()
    # The chokepoint uses strict less-than.
    assert "ts < " in sql, f"expected `ts < ` in WHERE, got: {sql!r}"
    # And NOT inclusive.
    assert "ts <=" not in sql, f"expected strict `<`, found `<=` in: {sql!r}"


def test_closes_as_of_runtime_assertion_catches_leak():
    """Force a leak by handing back a bar with ts == as_of, verify the
    Python-side defensive assertion fires."""
    as_of = _eod(date(2026, 4, 1))

    class _LeakySession(FakeSession):
        async def execute(self, stmt):
            self.execute_calls.append(stmt)
            # Pretend the WHERE clause was broken and let a future bar slip
            # through. The Python-side check should catch it.
            future_bar = _Bar(ts=as_of + timedelta(days=2), close=4.0)
            return _FakeResult([(future_bar.ts, future_bar.close)])

    session = _LeakySession(bars=[])
    with pytest.raises(RuntimeError, match="look-ahead detected"):
        asyncio.run(_closes_as_of(session, uuid.uuid4(), as_of))


# ── Property tests on _storage_as_of ──────────────────────────────────────


def test_storage_as_of_returns_only_published_reports():
    reports = [
        _Storage(report_date=date(2026, 3, 26), surprise_bcf=5.0, net_change_bcf=10.0),
        _Storage(report_date=date(2026, 4, 2), surprise_bcf=-3.0, net_change_bcf=20.0),
        _Storage(report_date=date(2026, 4, 9), surprise_bcf=8.0, net_change_bcf=30.0),
    ]
    session = FakeSession(storage_reports=reports)

    # As-of mid-April should see the Apr 2 release but NOT Apr 9.
    as_of = _eod(date(2026, 4, 5))
    result = asyncio.run(_storage_as_of(session, as_of, "NG"))
    assert result is not None
    assert result["delta_vs_consensus"] == -3.0
    assert result["actual_bcf"] == 20.0


def test_storage_as_of_excludes_same_day_release_after_as_of_date():
    """A release with report_date in the future relative to as_of must NOT appear."""
    reports = [
        _Storage(report_date=date(2026, 4, 9), surprise_bcf=10.0, net_change_bcf=15.0),
    ]
    session = FakeSession(storage_reports=reports)
    as_of = _eod(date(2026, 4, 8))  # Wednesday — Thursday release not out yet.
    result = asyncio.run(_storage_as_of(session, as_of, "NG"))
    assert result is None


def test_storage_as_of_returns_none_when_no_reports():
    session = FakeSession(storage_reports=[])
    as_of = _eod(date(2026, 4, 1))
    assert asyncio.run(_storage_as_of(session, as_of, "NG")) is None


def test_storage_as_of_non_ng_symbol_gets_none():
    """31a.0: eia_storage_reports is NG national storage — feeding it to any
    other symbol's backtest was cross-commodity contamination. Non-NG symbols
    must get None even when rows exist."""
    reports = [
        _Storage(report_date=date(2026, 4, 2), surprise_bcf=-3.0, net_change_bcf=20.0),
        _Storage(report_date=date(2026, 3, 26), surprise_bcf=5.0, net_change_bcf=10.0),
    ]
    session = FakeSession(storage_reports=reports)
    as_of = _eod(date(2026, 4, 5))
    for symbol in ("CL", "GC", "SI", "ES", "ZN"):
        assert asyncio.run(_storage_as_of(session, as_of, symbol)) is None
    # The queries never even hit the DB for non-NG symbols.
    assert session.execute_calls == []


def test_storage_as_of_seasonal_norm_proxy_when_no_consensus():
    """31a.0: real EIA rows carry surprise_bcf=None. The seasonal-surprise
    proxy (net change vs the same-calendar-week 5-year average) must carry
    the storage leg instead of the leg silently dying (or crashing)."""

    def storage_row(week_ending: date, net_change: float) -> _Storage:
        return _Storage(
            report_date=week_ending + timedelta(days=6),  # publication Thursday
            surprise_bcf=None,  # real-EIA shape: no consensus survey
            net_change_bcf=net_change,
            week_ending=week_ending,
        )

    current_week = date(2026, 4, 3)  # Friday
    priors = [
        storage_row(date(2025, 4, 4), 10.0),
        storage_row(date(2024, 4, 5), 12.0),
        storage_row(date(2023, 3, 31), 14.0),
        storage_row(date(2022, 4, 1), 12.0),
    ]
    session = FakeSession(storage_reports=[storage_row(current_week, 20.0), *priors])
    as_of = _eod(date(2026, 4, 10))
    result = asyncio.run(_storage_as_of(session, as_of, "NG"))
    assert result is not None
    assert result["delta_vs_consensus"] is None
    # norm = (10 + 12 + 14 + 12) / 4 = 12 → delta = 20 - 12 = 8.
    assert result["delta_vs_norm"] == pytest.approx(8.0)
    assert result["actual_bcf"] == 20.0


# ── Property tests on _cot_as_of ──────────────────────────────────────────


def test_cot_as_of_requires_two_reports_for_delta():
    reports = [
        _Cot(release_date=date(2026, 4, 3), managed_money_net=120_000),
    ]
    session = FakeSession(cot_reports=reports)
    as_of = _eod(date(2026, 4, 10))
    # Only one report exists → no WoW delta available → None.
    assert asyncio.run(_cot_as_of(session, as_of, "023651")) is None


def test_cot_as_of_computes_delta_from_two_most_recent():
    reports = [
        _Cot(release_date=date(2026, 3, 27), managed_money_net=100_000),
        _Cot(release_date=date(2026, 4, 3), managed_money_net=120_000),
        _Cot(release_date=date(2026, 4, 10), managed_money_net=140_000),
    ]
    session = FakeSession(cot_reports=reports)

    # As-of Apr 10 EOD: most recent two are Apr 10 (140k) and Apr 3 (120k).
    as_of = _eod(date(2026, 4, 10))
    result = asyncio.run(_cot_as_of(session, as_of, "023651"))
    assert result == {"mm_net_delta": 20_000.0}


def test_cot_as_of_excludes_future_release():
    """Apr 10 release is in the future as of Apr 9 — must not appear in the
    pair used for delta computation."""
    reports = [
        _Cot(release_date=date(2026, 3, 27), managed_money_net=100_000),
        _Cot(release_date=date(2026, 4, 3), managed_money_net=120_000),
        _Cot(release_date=date(2026, 4, 10), managed_money_net=140_000),
    ]
    session = FakeSession(cot_reports=reports)
    as_of = _eod(date(2026, 4, 9))
    result = asyncio.run(_cot_as_of(session, as_of, "023651"))
    # Pair is Apr 3 (120k) and Mar 27 (100k) → delta = +20k.
    assert result == {"mm_net_delta": 20_000.0}


def test_cot_as_of_filters_by_market_code():
    """31a.0 landmine lock: CFTC releases every market on the same Friday, so
    an unfiltered "two most recent rows" mixes different commodities'
    managed-money nets. The delta must come from ONE market only.

    Fail-without/pass-with: if the market filter is removed from the query,
    the fake session returns the global two most recent rows — one NG + one
    CL — and the assertion below fails on a cross-commodity delta.
    """
    ng_code, cl_code = "023651", "067651"
    reports = [
        # Colliding release dates, interleaved — exactly what a real 6-symbol
        # backfill looks like every week.
        _Cot(date(2026, 4, 3), 100_000, ng_code),
        _Cot(date(2026, 4, 3), 500_000, cl_code),
        _Cot(date(2026, 4, 10), 120_000, ng_code),
        _Cot(date(2026, 4, 10), 900_000, cl_code),
    ]
    session = FakeSession(cot_reports=reports)
    as_of = _eod(date(2026, 4, 10))
    assert asyncio.run(_cot_as_of(session, as_of, ng_code)) == {
        "mm_net_delta": 20_000.0
    }
    assert asyncio.run(_cot_as_of(session, as_of, cl_code)) == {
        "mm_net_delta": 400_000.0
    }
    # And the statements actually carried the filter (SQL-level proof).
    for stmt in session.execute_calls:
        sql = str(stmt.compile(compile_kwargs={"literal_binds": True})).lower()
        assert "cftc_contract_market_code" in sql


# ── Property test on _context_as_of (full context) ────────────────────────


def test_context_as_of_assembles_clean_snapshot():
    bars = _bars_from(date(2026, 2, 1), 90)
    storage = [
        _Storage(report_date=date(2026, 3, 26), surprise_bcf=2.0, net_change_bcf=5.0),
        _Storage(report_date=date(2026, 4, 2), surprise_bcf=-1.0, net_change_bcf=12.0),
    ]
    cot = [
        _Cot(release_date=date(2026, 3, 27), managed_money_net=100_000),
        _Cot(release_date=date(2026, 4, 3), managed_money_net=110_000),
    ]
    session = FakeSession(bars=bars, storage_reports=storage, cot_reports=cot)
    as_of = _eod(date(2026, 4, 5))

    ctx = asyncio.run(_context_as_of(session, "NG", uuid.uuid4(), as_of))
    assert ctx.symbol == "NG"
    assert len(ctx.closes) > 0
    # delta_vs_norm is None here: no week_ending / prior-year history in the
    # fixture, so the seasonal-norm proxy honestly abstains.
    assert ctx.latest_storage == {
        "delta_vs_consensus": -1.0,
        "delta_vs_norm": None,
        "actual_bcf": 12.0,
    }
    assert ctx.latest_cot == {"mm_net_delta": 10_000.0}


def test_context_as_of_symbol_without_cot_market_gets_no_cot():
    """31a.0: a symbol with no registered CFTC market (index/rates classes)
    must get latest_cot=None — never another commodity's positioning — and
    non-NG symbols get no NG storage."""
    bars = _bars_from(date(2026, 2, 1), 90)
    storage = [
        _Storage(report_date=date(2026, 4, 2), surprise_bcf=-1.0, net_change_bcf=12.0),
    ]
    cot = [
        _Cot(date(2026, 3, 27), 100_000),
        _Cot(date(2026, 4, 3), 110_000),
    ]
    session = FakeSession(bars=bars, storage_reports=storage, cot_reports=cot)
    as_of = _eod(date(2026, 4, 5))

    ctx = asyncio.run(_context_as_of(session, "ES", uuid.uuid4(), as_of))
    assert ctx.latest_cot is None
    assert ctx.latest_storage is None


# ── Cheating-model proof ──────────────────────────────────────────────────


def _cheating_predict(model_name: str, ctx, horizon: str) -> ForecastResult:
    """A 'model' that would score 100% if ctx.closes leaked the future.

    If ctx.closes only contains bars strictly before as_of (correct), then
    ctx.closes[-1] is the anchor close (= start_close for realized_pct), and
    ctx.closes[-2] is one bar earlier — basically yesterday's momentum.
    Predicting direction off yesterday's momentum on a chaotic series gets
    you coin-flip.

    If ctx.closes EXTENDED through as_of + horizon (BUG), then ctx.closes[-1]
    would be the future close at the horizon — predicting direction from
    that would be trivially perfect.

    The boundary case where ctx.closes goes through as_of itself (instead of
    strictly before) would still be coin-flip in practice because as_of's
    close ≈ the anchor.
    """
    if len(ctx.closes) < 2:
        direction = "neutral"
    else:
        direction = "bullish" if ctx.closes[-1] > ctx.closes[-2] else "bearish"
    return ForecastResult(
        model_name="cheating_test_model",
        horizon=horizon,
        direction=direction,
        confidence="high",
        expected_pct=0.0,
        range_low_pct=-0.02,
        range_high_pct=0.02,
        vol_regime=None,
        supporting=[],
        contradicting=[],
        inputs_used=["closes"],
    )


def test_cheating_model_does_not_score_100_percent():
    """End-to-end proof: even a model designed to exploit any leaked future
    in ctx.closes still gets bounded by chance, because the chokepoint
    blocks future bars from ever entering the context.

    If this test ever sees hit_rate near 100%, look-ahead leaked into ctx.
    """
    import random

    # Deterministic random walk — NG-shaped, choppy enough that
    # yesterday's direction is uninformative about tomorrow's.
    rng = random.Random(42)
    n = 200
    bars: list[_Bar] = []
    price = 3.0
    for i in range(n):
        price *= 1.0 + rng.gauss(0.0, 0.015)
        bars.append(
            _Bar(
                ts=datetime(2026, 1, 1) + timedelta(days=i),
                close=max(price, 0.5),
            )
        )

    session = FakeSession(bars=bars)
    # We need _resolve_contract_id to return something; monkey-patch it
    # for the test by also defining a dummy session.execute path for the
    # instruments + contracts queries. Easier: patch the resolver.
    from unittest.mock import patch

    import apps.api.services.backtest as backtest_mod

    async def _fake_resolve(_session, _symbol):
        return uuid.UUID("00000000-0000-0000-0000-000000000001")

    config = BacktestConfig(
        model_name="moving_average_directional",  # any valid name; predict_fn overrides
        from_date=date(2026, 4, 1),
        to_date=date(2026, 7, 1),
        horizon="1d",
    )
    with patch.object(backtest_mod, "_resolve_contract_id", new=_fake_resolve):
        rows, summary = asyncio.run(
            run_backtest(session, config, predict_fn=_cheating_predict)
        )

    assert summary.scored >= 30, (
        f"need a meaningful sample to evaluate hit_rate; got scored={summary.scored}"
    )
    # The killer assertion. If chokepoint is correctly enforced, the cheating
    # model — which would score 100% with leaked future data — instead scores
    # near coin-flip. 0.65 leaves plenty of room for chance fluctuations on a
    # ~60-row sample while still being WAY below the ~1.0 a real leak would
    # produce.
    assert summary.hit_rate <= 0.65, (
        f"Look-ahead suspected: cheating model scored hit_rate={summary.hit_rate:.3f} "
        f"({summary.scored} scored). Inspect _closes_as_of and _context_as_of."
    )
