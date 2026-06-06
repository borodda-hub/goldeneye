"""Real historical price backfill — Yahoo daily OHLC into the `price_bars`
hypertable, retiring seeded GBM for the showcase.

This generalizes the one-off `seeds/_backfill_cl_prices.py` into a reusable,
instrument-agnostic service: resolve an instrument by symbol, pull real daily
bars for each of its contracts via the market adapter, and upsert them
idempotently (ON CONFLICT DO NOTHING on the (ts, contract_id, resolution) PK).
Backfilled rows are tagged `source="yahoo_delayed"` so they're distinguishable
from seeded `source="mock"` bars.

`replace_mock=True` swaps a contract's seeded GBM daily bars for the real series
— but only after a non-empty real fetch succeeds, so a network failure can never
leave a contract with no data. Used for NG (the GBM showcase symbol); the other
five (CL/HO/RB/GC/SI) carry no mock bars, so they just accumulate real ones.

Asset-class-agnostic by design: nothing here is commodity-specific, so a new
asset class is a new market adapter + instrument rows, not a rewrite — the
template every future asset class reuses (see docs/CALIBRATION_ROADMAP.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.orm.contracts import Contract
from apps.api.models.orm.instruments import Instrument
from apps.api.models.orm.prices import PriceBar

BACKFILL_SOURCE = "yahoo_delayed"
DEFAULT_LOOKBACK_DAYS = 730  # ~2y of daily history (matches the prior GBM depth)


class _Market(Protocol):
    """The slice of the market adapter this service needs."""

    async def get_bars(
        self, contract_code: str, resolution: str, from_dt: datetime, to_dt: datetime
    ) -> list[dict[str, Any]]: ...


@dataclass
class BackfillResult:
    symbol: str
    contracts_seen: int = 0
    contracts_filled: int = 0
    bars_inserted: int = 0
    mock_bars_removed: int = 0
    per_contract: dict[str, int] = field(default_factory=dict)
    note: str | None = None


def _bars_to_rows(
    contract_id: Any,
    bars: list[dict[str, Any]],
    *,
    resolution: str,
    source: str = BACKFILL_SOURCE,
) -> list[dict[str, Any]]:
    """Map adapter bar dicts to `price_bars` row dicts. Pure + unit-testable."""
    return [
        {
            "contract_id": contract_id,
            "resolution": resolution,
            "ts": b["ts"],
            "open": b["open"],
            "high": b["high"],
            "low": b["low"],
            "close": b["close"],
            "volume": b.get("volume") or 0,
            "source": source,
        }
        for b in bars
    ]


async def backfill_instrument(
    session: AsyncSession,
    market: _Market,
    symbol: str,
    *,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    resolution: str = "1d",
    replace_mock: bool = False,
) -> BackfillResult:
    """Backfill real daily bars for every contract of one instrument.

    Idempotent: re-runs insert only new (ts, contract_id, resolution) rows. When
    `replace_mock` is set, a contract's seeded `source="mock"` bars at this
    resolution are deleted *after* a non-empty real fetch, then replaced — so a
    failed/empty fetch is a no-op rather than a data-loss.
    """
    result = BackfillResult(symbol=symbol)

    instr_id = (
        await session.execute(select(Instrument.id).where(Instrument.symbol == symbol))
    ).scalar_one_or_none()
    if instr_id is None:
        result.note = f"instrument {symbol!r} not seeded — run load_fixtures first"
        return result

    contracts = (
        await session.execute(
            select(Contract.id, Contract.contract_code).where(
                Contract.instrument_id == instr_id
            )
        )
    ).all()
    if not contracts:
        result.note = f"no contracts seeded for {symbol!r}"
        return result

    to_dt = datetime.now(UTC).replace(tzinfo=None)
    from_dt = to_dt - timedelta(days=lookback_days)

    for contract_id, contract_code in contracts:
        result.contracts_seen += 1
        try:
            bars = await market.get_bars(contract_code, resolution, from_dt, to_dt)
        except Exception as exc:  # adapter already degrades, but be defensive
            result.per_contract[contract_code] = -1
            result.note = f"{contract_code}: fetch failed — {exc}"
            continue
        if not bars:
            result.per_contract[contract_code] = 0
            continue

        if replace_mock:
            removed = await session.execute(
                delete(PriceBar).where(
                    PriceBar.contract_id == contract_id,
                    PriceBar.resolution == resolution,
                    PriceBar.source == "mock",
                )
            )
            result.mock_bars_removed += removed.rowcount or 0

        rows = _bars_to_rows(contract_id, bars, resolution=resolution)
        inserted = await session.execute(
            pg_insert(PriceBar).values(rows).on_conflict_do_nothing()
        )
        n = inserted.rowcount or 0
        result.bars_inserted += n
        result.contracts_filled += 1
        result.per_contract[contract_code] = n

    return result
