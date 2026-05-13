"""Phase 14 step 3 — cot_repo filter by market code."""
from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import AsyncMock

import pytest

from apps.api.repos import cot as cot_repo


class _FakeResult:
    def __init__(self, rows: list[object]):
        self._rows = rows

    def scalars(self):
        rows = self._rows

        class _S:
            def all(self_inner):
                return rows

        return _S()

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None


@pytest.mark.asyncio
async def test_get_recent_without_filter_omits_where_clause():
    """Backwards-compat: passing no market code should not add a filter."""
    session = AsyncMock()
    captured: dict[str, object] = {}

    async def fake_execute(stmt):
        captured["stmt"] = stmt
        return _FakeResult([])

    session.execute = fake_execute
    out = await cot_repo.get_recent(session, limit=10)
    assert out == []
    sql_text = str(captured["stmt"]).upper()
    # The column name appears in the SELECT clause; what we care about is
    # that no equality predicate on it was added.
    assert "CFTC_CONTRACT_MARKET_CODE = " not in sql_text


@pytest.mark.asyncio
async def test_get_recent_with_filter_emits_where_on_market_code():
    session = AsyncMock()
    captured: dict[str, object] = {}

    async def fake_execute(stmt):
        captured["stmt"] = stmt
        return _FakeResult([])

    session.execute = fake_execute
    await cot_repo.get_recent(
        session, limit=10, cftc_contract_market_code="067651"
    )
    sql_text = str(captured["stmt"]).upper()
    # The market-code equality predicate appears in the SQL.
    assert "CFTC_CONTRACT_MARKET_CODE = " in sql_text


@pytest.mark.asyncio
async def test_get_latest_with_filter_emits_where_on_market_code():
    session = AsyncMock()
    captured: dict[str, object] = {}

    async def fake_execute(stmt):
        captured["stmt"] = stmt
        return _FakeResult([])

    session.execute = fake_execute
    await cot_repo.get_latest(session, cftc_contract_market_code="023651")
    sql_text = str(captured["stmt"]).upper()
    assert "CFTC_CONTRACT_MARKET_CODE = " in sql_text


@pytest.mark.asyncio
async def test_get_latest_without_filter_returns_any_row():
    """No filter → any market's row qualifies."""
    fake_row = type(
        "R", (), {"id": uuid.uuid4(), "report_date": date(2026, 5, 5)}
    )()
    session = AsyncMock()

    async def fake_execute(stmt):
        return _FakeResult([fake_row])

    session.execute = fake_execute
    result = await cot_repo.get_latest(session)
    assert result is fake_row
