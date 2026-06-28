"""Backfill real daily price history for all showcase instruments.

Run with:  python -m apps.api.seeds.backfill_prices [SYMBOL ...]

Pulls ~2y of real 1d bars from Yahoo into `price_bars` for each instrument's
contracts, tagged source="yahoo_delayed". Idempotent — safe to re-run. NG is
the GBM showcase symbol, so its seeded mock daily bars are replaced with the
real series (only after a successful non-empty fetch). The others carry no mock
bars and simply accumulate real ones.

Supersedes the CL-only one-off `_backfill_cl_prices.py`. Writes to whatever
DATABASE_URL points at — run it against a dev/staging DB; promoting real data to
production is a deliberate, separate step (see docs/CALIBRATION_ROADMAP.md).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# NG first (it's the GBM showcase → replace_mock); the rest accumulate real bars.
# ES (index) + ZN (rates) are the B5 cross-asset classes — real bars via Yahoo.
DEFAULT_SYMBOLS = ["NG", "CL", "HO", "RB", "GC", "SI", "ES", "ZN"]
REPLACE_MOCK_SYMBOLS = {"NG"}


async def go(symbols: list[str]) -> None:
    from apps.api.adapters.registry import get_market
    from apps.api.db.session import get_session_factory
    from apps.api.services.price_backfill import backfill_instrument

    market = get_market()
    session_factory = get_session_factory()

    grand_total = 0
    async with session_factory() as session:
        async with session.begin():
            for symbol in symbols:
                res = await backfill_instrument(
                    session,
                    market,
                    symbol,
                    replace_mock=symbol in REPLACE_MOCK_SYMBOLS,
                )
                if res.note:
                    print(f"{symbol}: {res.note}")
                replaced = (
                    f", replaced {res.mock_bars_removed} mock"
                    if res.mock_bars_removed
                    else ""
                )
                print(
                    f"{symbol}: +{res.bars_inserted} bars across "
                    f"{res.contracts_filled}/{res.contracts_seen} contracts{replaced}"
                )
                grand_total += res.bars_inserted
    print(f"\nBackfill complete — {grand_total} new real bars inserted.")


if __name__ == "__main__":
    args = [a.upper() for a in sys.argv[1:]] or DEFAULT_SYMBOLS
    asyncio.run(go(args))
