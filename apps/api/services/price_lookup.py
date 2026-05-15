"""Unified daily-close lookup that survives the price_bars seed hole.

Today, only NGM26 has rows in the `price_bars` table — the other front-month
contracts (CL, HO, RB, GC, SI) all rely on the live market adapter for their
candlesticks. The DB-only `price_bars_repo.get_latest_n_closes` therefore
returns an empty list for them, and every read path that fed those closes
into a scoring / ensemble / display layer silently degraded.

`get_latest_closes` here is the single fallback-aware helper. It tries the
DB first (cheap, deterministic, exact) and falls back to the market adapter
when the DB is empty. Errors from either layer are swallowed and surface as
"no closes", so callers don't have to handle adapter outages on top of
their own logic.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.adapters.registry import get_market
from apps.api.repos import price_bars as price_repo

logger = logging.getLogger(__name__)


async def get_latest_closes(
    session: AsyncSession,
    *,
    contract_id: uuid.UUID | None,
    contract_code: str | None,
    n: int = 100,
    resolution: str = "1d",
) -> list[float]:
    """Latest `n` daily closes for the given contract, oldest-first.

    Lookup order:
      1. price_bars repo (DB) — fast, only works for seeded contracts (NGM26).
      2. Live market adapter — works for any front-month Yahoo serves.

    Either layer raising or returning empty is treated as "no closes" and
    falls through; the caller gets `[]` rather than an exception. The list
    is sorted ascending by time so existing ensemble code can index [-1]
    for "today" and [0] for "first available".
    """
    # 1. DB path
    if contract_id is not None:
        try:
            closes = await price_repo.get_latest_n_closes(
                session, contract_id, n=n, resolution=resolution
            )
        except Exception as exc:
            logger.warning("DB close lookup failed: %s", exc)
            closes = []
        if closes:
            # repo already returns ascending-by-time order; preserve it.
            return [float(c) for c in closes]

    # 2. Market adapter fallback
    if not contract_code:
        return []
    try:
        market = get_market()
        now = datetime.utcnow()
        # 2× n calendar days covers weekends + holidays comfortably.
        bars = await market.get_bars(
            contract_code,
            resolution,
            from_dt=now - timedelta(days=max(n * 2, 14)),
            to_dt=now,
        )
    except Exception as exc:
        logger.warning(
            "market adapter close lookup failed for %s: %s", contract_code, exc
        )
        return []
    if not bars:
        return []
    bars_sorted = sorted(bars, key=lambda b: b["ts"])
    closes = [float(b["close"]) for b in bars_sorted[-n:] if b.get("close") is not None]
    return closes
