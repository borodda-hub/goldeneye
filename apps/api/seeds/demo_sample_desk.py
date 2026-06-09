"""Seed LABELED blind-strategy sample desks (Phase B1).

With zero real users, the showcase IS the product — but it must be HONEST. So
instead of authoring outcomes, we seed three **blind strategy desks** whose
direction is fixed by a fixed rule **before the outcome is known**, then let the
auto-resolution engine score them against real price moves and show *whatever*
calibration / skill-vs-luck actually emerges:

  - momentum   — predict continuation of the prior 20-day return (user_id NULL,
                 the anonymous sample desk → drives the per-instrument reliability diagram)
  - contrarian — predict reversal of the prior 20-day return
  - random     — a deterministic coin-flip (the luck baseline)

THE LINE (docs/PHASE_B1_PLAN.md §11.1): direction is NEVER chosen to force a hit;
it is the strategy's blind call. Conviction is a function of *signal strength*
(quantile of |prior return|), computed from pre-decision data only — never from
the outcome. We curate WHICH strategies to show; we do not rig individual results.
The resulting curve is real — imperfect-but-real, not tuned toward a target shape.

Always surfaced under: "Sample desk — illustrative strategies (momentum / contrarian
/ random) scored on real prices; not a real analyst track record."

Idempotent: deletes prior `[sample-desk]` rows (its three desks), re-inserts. Run:
    python -m apps.api.seeds.demo_sample_desk
"""

from __future__ import annotations

import asyncio
import random
import sys
import uuid
from datetime import datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_MARKER = "[sample-desk]"
_INSTRUMENTS = ["NG", "CL"]  # concentrated so per-instrument calibration buckets are meaningful
_LOOKBACK = 20   # trading days of prior return that the momentum/contrarian signal reads
_HORIZON = 15    # trading days from anchor to target (the elapsed horizon)
_STEP = 6        # window stride
_THRESHOLD_PCT = 0.4  # deadband; sub-threshold moves resolve neutral (excluded from buckets)
_BUCKET_CONV = [10, 30, 50, 70, 90]  # conviction = quintile of |signal| (blind to outcome)

# Deterministic ids so re-runs replace, not duplicate. All three desks are named
# (own user_id) — the QUANT-PROOF layer (desk leaderboard) for technical
# conversations. The NULL pool is reserved for the hero sample-analyst
# (demo_sample_analyst.py), so it isn't polluted by these desks.
_NS = uuid.UUID("5a3b1e00-0000-4000-8000-000000000000")
_MOMENTUM_UID = uuid.uuid5(_NS, "momentum")
_CONTRARIAN_UID = uuid.uuid5(_NS, "contrarian")
_RANDOM_UID = uuid.uuid5(_NS, "random")


def _opposite(direction: str) -> str:
    return "bearish" if direction == "bullish" else "bullish"


async def go() -> None:
    import apps.api.models.orm.contracts  # noqa: F401
    import apps.api.models.orm.instruments  # noqa: F401
    import apps.api.models.orm.theses  # noqa: F401  (FK target for thesis_id_at_write)
    import apps.api.models.orm.journal  # noqa: F401
    import apps.api.models.orm.prices  # noqa: F401
    from sqlalchemy import delete, select

    from apps.api.db.session import get_session_factory
    from apps.api.models.orm.instruments import Instrument
    from apps.api.models.orm.journal import UserDecisionJournal
    from apps.api.models.orm.prices import PriceBar
    from apps.api.repos import contracts as contract_repo

    rng = random.Random(7)

    async with get_session_factory()() as s:
        # Wipe prior sample-desk rows (all three desks) so re-runs replace.
        await s.execute(
            delete(UserDecisionJournal).where(
                UserDecisionJournal.hypothesis.like(f"{_MARKER}%"),
                UserDecisionJournal.user_id.in_(
                    [_MOMENTUM_UID, _CONTRARIAN_UID, _RANDOM_UID]
                ),
            )
        )

        # Build the window list (blind): for each instrument, slide over the front
        # contract's real bars. The signal reads ONLY prior bars; the outcome bar is
        # never consulted here.
        windows: list[tuple] = []  # (inst_id, sym, anchor_bar, target_bar, signal)
        for sym in _INSTRUMENTS:
            inst = (
                await s.execute(select(Instrument).where(Instrument.symbol == sym))
            ).scalar_one_or_none()
            if inst is None:
                continue
            front = await contract_repo.get_front_month(s, inst.id)
            if front is None:
                continue
            bars = list(
                (
                    await s.execute(
                        select(PriceBar)
                        .where(PriceBar.contract_id == front.id, PriceBar.resolution == "1d")
                        .order_by(PriceBar.ts.asc())
                    )
                ).scalars().all()
            )
            for start in range(_LOOKBACK, len(bars) - _HORIZON, _STEP):
                signal = float(bars[start].close) / float(bars[start - _LOOKBACK].close) - 1.0
                windows.append((inst.id, sym, bars[start], bars[start + _HORIZON], signal))

        if not windows:
            print("error: no front-month price coverage — run load_fixtures + backfill first")
            return

        # Conviction = quintile of |signal| (signal strength), computed across all
        # windows — pre-decision data only, never the outcome.
        order = sorted(range(len(windows)), key=lambda j: abs(windows[j][4]))
        conv_of: dict[int, int] = {}
        for rank, j in enumerate(order):
            conv_of[j] = _BUCKET_CONV[min(4, rank * 5 // len(order))]

        def _add(uid, label, inst_id, sym, anchor_bar, target_bar, direction, conviction):
            a_date, t_date = anchor_bar.ts.date(), target_bar.ts.date()
            s.add(
                UserDecisionJournal(
                    id=uuid.uuid4(),
                    created_at=datetime(a_date.year, a_date.month, a_date.day),
                    user_id=uid,
                    instrument_id=inst_id,
                    hypothesis=f"{_MARKER} {label} {sym} {direction} ({conviction}% conv)",
                    evidence=[],
                    confidence_pct=conviction,
                    predicted_direction=direction,
                    horizon_days=(t_date - a_date).days,
                    threshold_pct=_THRESHOLD_PCT,
                    anchor_price=float(anchor_bar.close),
                    resolved_direction=None,  # OPEN — the scheduler resolves it on real prices
                    auto_resolved=False,
                )
            )

        total = 0
        for j, (inst_id, sym, anchor_bar, target_bar, signal) in enumerate(windows):
            conv = conv_of[j]
            up = signal > 0
            # momentum: continuation.
            _add(_MOMENTUM_UID, "momentum", inst_id, sym, anchor_bar, target_bar,
                 "bullish" if up else "bearish", conv)
            # contrarian: reversal.
            _add(_CONTRARIAN_UID, "contrarian", inst_id, sym, anchor_bar, target_bar,
                 "bearish" if up else "bullish", conv)
            # random: coin-flip direction + coin-flip conviction (the luck baseline).
            _add(_RANDOM_UID, "random", inst_id, sym, anchor_bar, target_bar,
                 rng.choice(["bullish", "bearish"]), rng.choice(_BUCKET_CONV))
            total += 3

        await s.commit()
        print(
            f"Seeded {total} OPEN blind-strategy decisions across {len(windows)} windows "
            f"(momentum=NULL pool, contrarian/random named). Directions are fixed by each "
            f"strategy's rule BEFORE the outcome. Resolve to reveal the real calibration."
        )


if __name__ == "__main__":
    asyncio.run(go())
