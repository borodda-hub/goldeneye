"""Delayed-quote poller. Replaces the synthetic ticker when ADAPTER_MARKET is
configured to point at a real (delayed) feed.

Behavior:
- Every `_POLL_INTERVAL` seconds (default 60s) pull the latest 1m bar via the
  market-data adapter.
- Emit a `tick` event on `price.NG.front` every poll (whether or not the bar
  changed) so the dashboard's "is the feed alive?" indicator keeps pulsing.
- Emit a `bar` event on `price.NG.front.1m` only when the bar's timestamp
  has moved forward (avoids duplicate-bar spam in the WS stream).

Signal updates are NOT emitted here — signals are computed on demand by
`/v1/signals/current`. The synthetic signal loop in ticker.py was decorative;
removing it under the real path is the honest move (we can't tell when a
signal has changed without re-running the ensemble, which is request-priced).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from apps.api.adapters.registry import get_market
from apps.api.realtime.gateway import broadcast

logger = logging.getLogger(__name__)

_SYMBOL = "NG"
_FRONT_CONTRACT_FALLBACK = "NGM26"
_POLL_INTERVAL = 60  # seconds


async def _resolve_front_contract() -> str:
    """Best-effort front-month resolution. Real path goes via the contracts
    repo at startup, but we don't have a DB session here — fall back to the
    hardcoded current front month."""
    return _FRONT_CONTRACT_FALLBACK


async def _poll_loop() -> None:
    market = get_market()
    contract = await _resolve_front_contract()
    last_bar_ts: datetime | None = None

    while True:
        try:
            latest = await market.get_latest_price(contract)
        except Exception as exc:
            logger.warning("delayed-quote poller: market.get_latest_price failed: %s", exc)
            latest = None

        if latest:
            ts = latest.get("ts")
            close = latest.get("close")
            ts_iso = ts.isoformat() if isinstance(ts, datetime) else str(ts) if ts else None

            # Tick heartbeat — fires every poll so the WS keeps a pulse.
            await broadcast(
                f"price.{_SYMBOL}.front",
                "tick",
                {
                    "ts": datetime.utcnow().isoformat(),
                    "contract_code": contract,
                    "price": round(float(close), 4) if close is not None else None,
                    "source": latest.get("source", "delayed"),
                    "delayed": True,
                    "quote_ts": ts_iso,
                },
            )

            # New bar — only emit when ts has advanced.
            if isinstance(ts, datetime) and ts != last_bar_ts:
                last_bar_ts = ts
                await broadcast(
                    f"price.{_SYMBOL}.front.1m",
                    "bar",
                    {
                        "ts": ts_iso,
                        "o": _round(latest.get("open")),
                        "h": _round(latest.get("high")),
                        "l": _round(latest.get("low")),
                        "c": _round(latest.get("close")),
                        "v": int(latest.get("volume") or 0),
                        "source": latest.get("source", "delayed"),
                        "delayed": True,
                    },
                )

        await asyncio.sleep(_POLL_INTERVAL)


def _round(value: Any) -> float | None:
    return round(float(value), 4) if value is not None else None


async def start_delayed_poller() -> None:
    """Launch the delayed-quote poller as a background task."""
    asyncio.create_task(_poll_loop())
    logger.info("Delayed-quote poller started")
