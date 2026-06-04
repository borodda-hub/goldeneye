"""Positioning service — latest CFTC managed-money positioning per instrument.

Reads the instrument's `cftc_market_code` (seeded in instruments.json metadata)
and returns the most recent COT report's managed-money net, the week-over-week
delta, and open interest. Instruments without a CFTC market code (or with no COT
rows seeded) return an `available: false` empty state.

Raw factual data — no safety wrapper.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.orm.instruments import Instrument
from apps.api.repos import cot as cot_repo


def _unavailable(symbol: str) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "available": False,
        "report_date": None,
        "release_date": None,
        "managed_money_net": None,
        "managed_money_long": None,
        "managed_money_short": None,
        "mm_net_delta": None,
        "open_interest_total": None,
        "source": None,
    }


def _int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


async def get_positioning(session: AsyncSession, instrument: Instrument) -> dict[str, Any]:
    symbol = instrument.symbol

    market_code: str | None = None
    if isinstance(instrument.metadata_, dict):
        market_code = instrument.metadata_.get("cftc_market_code") or None
    if not market_code:
        return _unavailable(symbol)

    rows = await cot_repo.get_recent(
        session, limit=2, cftc_contract_market_code=market_code
    )
    if not rows:
        return _unavailable(symbol)

    latest = rows[0]
    mm_net = _int(latest.managed_money_net)

    mm_net_delta: int | None = None
    if len(rows) >= 2:
        prev_net = _int(rows[1].managed_money_net)
        if mm_net is not None and prev_net is not None:
            mm_net_delta = mm_net - prev_net

    return {
        "symbol": symbol,
        "available": True,
        "report_date": latest.report_date.isoformat() if latest.report_date else None,
        "release_date": latest.release_date.isoformat() if latest.release_date else None,
        "managed_money_net": mm_net,
        "managed_money_long": _int(latest.managed_money_long),
        "managed_money_short": _int(latest.managed_money_short),
        "mm_net_delta": mm_net_delta,
        "open_interest_total": _int(latest.open_interest_total),
        "source": latest.source or "CFTC_PRE",
    }
