"""One-shot CL seed runner. Run with:
    python -m apps.api.seeds._run_seed_cl

Idempotent: seed_forecasts skips when rows already exist for the instrument.
Safe to re-run.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


async def go() -> None:
    from apps.api.db.session import get_session_factory
    from apps.api.seeds.example_forecasts import seed_forecasts
    import apps.api.models.orm.instruments  # noqa: F401
    import apps.api.models.orm.contracts  # noqa: F401
    import apps.api.models.orm.forecasts  # noqa: F401
    import apps.api.models.orm.prices  # noqa: F401 — registers price_bars table

    session_factory = get_session_factory()
    async with session_factory() as session:
        async with session.begin():
            n = await seed_forecasts(session, "CL")
            print(f"inserted {n} CL forecast rows")


if __name__ == "__main__":
    asyncio.run(go())
