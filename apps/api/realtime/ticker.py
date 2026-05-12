"""
Synthetic tick emitter. Runs as a background task.

Every 2 seconds: emit a tick to price.NG.front
Every 60 seconds: emit a 1-minute bar to price.NG.front.1m
Every 300 seconds: emit a signal update to signal.NG
"""
from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime

from apps.api.realtime.gateway import broadcast

logger = logging.getLogger(__name__)

_BASE_PRICE = 3.20
_SYMBOL = "NG"
_FRONT_CONTRACT = "NGM26"
_TICK_INTERVAL = 2
_BAR_INTERVAL = 60
_SIGNAL_INTERVAL = 300


async def _tick_loop(rng: random.Random) -> None:
    price = _BASE_PRICE
    while True:
        await asyncio.sleep(_TICK_INTERVAL)
        # Small random walk
        price = max(0.10, price + rng.gauss(0, 0.003))
        size = rng.randint(1, 50)
        side = rng.choice(["bid", "ask"])
        await broadcast(
            f"price.{_SYMBOL}.front",
            "tick",
            {
                "ts": datetime.utcnow().isoformat(),
                "contract_code": _FRONT_CONTRACT,
                "price": round(price, 4),
                "size": size,
                "side": side,
            },
        )


async def _bar_loop(rng: random.Random) -> None:
    price = _BASE_PRICE
    while True:
        await asyncio.sleep(_BAR_INTERVAL)
        o = price
        c = max(0.10, price + rng.gauss(0, 0.01))
        h = max(o, c) * (1 + abs(rng.gauss(0, 0.005)))
        lo = min(o, c) * (1 - abs(rng.gauss(0, 0.005)))
        v = rng.randint(800, 3000)
        price = c
        await broadcast(
            f"price.{_SYMBOL}.front.1m",
            "bar",
            {
                "ts": datetime.utcnow().isoformat(),
                "o": round(o, 4),
                "h": round(h, 4),
                "l": round(lo, 4),
                "c": round(c, 4),
                "v": v,
            },
        )


async def _signal_loop(rng: random.Random) -> None:
    directions = ["bullish", "bearish", "neutral"]
    prev = "neutral"
    while True:
        await asyncio.sleep(_SIGNAL_INTERVAL)
        direction = rng.choice(directions)
        confidence = rng.choice(["low", "medium", "high"])
        delta = "flip" if direction != prev else "unchanged"
        prev = direction
        await broadcast(
            f"signal.{_SYMBOL}",
            "signal_update",
            {
                "direction": direction,
                "confidence": confidence,
                "delta_from_prev": delta,
                "ts": datetime.utcnow().isoformat(),
            },
        )


async def start_ticker() -> None:
    """Launch the WS feed appropriate for the configured market adapter.

    - ADAPTER_MARKET=yahoo_delayed (or any non-mock real adapter) → polled
      delayed-quote loop in delayed_quote_poller.py.
    - Otherwise → the synthetic tick/bar/signal loops in this module.
    """
    from apps.api.src.settings import settings

    if settings.adapter_market != "mock":
        from apps.api.realtime.delayed_quote_poller import start_delayed_poller

        await start_delayed_poller()
        return

    rng = random.Random(42)
    asyncio.create_task(_tick_loop(rng))
    asyncio.create_task(_bar_loop(rng))
    asyncio.create_task(_signal_loop(rng))
    logger.info("Synthetic ticker background tasks started (mock adapter)")
