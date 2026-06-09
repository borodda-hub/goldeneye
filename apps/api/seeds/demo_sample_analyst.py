"""Seed the HERO illustrative scenario — a sample analyst whose calibration
improves over ~6 months (Phase B1).

The buyer-facing story is "make your people better": one clearly-fictional sample
analyst, her decisions spread over six months, scored by the REAL calibration
engine against REAL `yahoo_delayed` prices.

THE HONEST LINE (docs/PHASE_B1_PLAN.md §11.1): we author her CONVICTION BEHAVIOR
changing over time — overconfident early, more measured later — and NEVER her
outcomes. Direction is a fixed blind rule (momentum / continuation of the prior
20-day return), chosen before the move is known. The engine resolves the genuine
realized move. If her reliability curve tightens and her "Your 90% theses resolved
at X%" line improves, it is because de-biased conviction met real prices — not
because any result was picked. No outcome-forcing anywhere.

Persona is explicitly fictional and lives in the anonymous (NULL) pool — the
signed-out demo view. Always surfaced under the illustrative-scenario label; never
a real testimonial.

Idempotent: clears prior NULL-pool *structured* decisions (so her view is clean of
legacy/strategy rows), re-inserts. Run:
    python -m apps.api.seeds.demo_sample_analyst
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import date, datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_MARKER = "[sample-analyst]"
_INSTRUMENTS = ["NG", "CL"]
_LOOKBACK = 20      # prior trading days the momentum signal reads
_HORIZONS = (10, 20)  # two real horizons → more real decisions to firm up thin buckets
_STEP = 2           # dense windows so each half-period's buckets clear n>=3
_THRESHOLD_PCT = 0.4
# Her honest (measured) conviction by signal-strength quintile — clusters near a
# modest true skill with spread, so the reliability diagram has a curve.
_BASE_CONV = [45, 52, 58, 64, 70]
_MAX_BIAS = 28      # early overconfidence added on top of honest conviction (decays to 0)
# Six-month decision window (anchor dates), inside the real price coverage so every
# horizon is already elapsed against a real close.
_WINDOW_START = date(2025, 11, 15)
_WINDOW_END = date(2026, 5, 12)


async def go() -> None:
    import apps.api.models.orm.contracts  # noqa: F401
    import apps.api.models.orm.instruments  # noqa: F401
    import apps.api.models.orm.theses  # noqa: F401  (FK target)
    import apps.api.models.orm.journal  # noqa: F401
    import apps.api.models.orm.prices  # noqa: F401
    from sqlalchemy import delete, select

    from apps.api.db.session import get_session_factory
    from apps.api.models.orm.instruments import Instrument
    from apps.api.models.orm.journal import UserDecisionJournal
    from apps.api.models.orm.prices import PriceBar
    from apps.api.repos import contracts as contract_repo

    async with get_session_factory()() as s:
        # Clean the NULL pool of *structured* decisions so the hero's reliability
        # view is hers alone (legacy prose entries — no predicted_direction — stay).
        await s.execute(
            delete(UserDecisionJournal).where(
                UserDecisionJournal.user_id.is_(None),
                UserDecisionJournal.predicted_direction.is_not(None),
            )
        )

        # Build blind windows within the 6-month band (signal reads prior bars only).
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
            for h in _HORIZONS:
                for start in range(_LOOKBACK, len(bars) - h, _STEP):
                    a_date = bars[start].ts.date()
                    if not (_WINDOW_START <= a_date <= _WINDOW_END):
                        continue
                    signal = float(bars[start].close) / float(bars[start - _LOOKBACK].close) - 1.0
                    windows.append((inst.id, sym, bars[start], bars[start + h], signal))

        if len(windows) < 20:
            print(f"error: only {len(windows)} windows in band — widen the band or step.")
            return

        # Time order (the arc axis) + signal-strength quintile (the conviction spread).
        windows.sort(key=lambda w: w[2].ts)
        n = len(windows)
        sig_rank = {j: r for r, j in enumerate(sorted(range(n), key=lambda j: abs(windows[j][4])))}

        for j, (inst_id, sym, anchor_bar, target_bar, signal) in enumerate(windows):
            base = _BASE_CONV[min(4, sig_rank[j] * 5 // n)]
            # Overconfidence bias decays linearly across the 6 months: heavy early, ~0 late.
            bias = round(_MAX_BIAS * (1.0 - j / (n - 1)))
            conviction = max(5, min(95, base + bias))
            direction = "bullish" if signal > 0 else "bearish"  # blind momentum call
            a_date, t_date = anchor_bar.ts.date(), target_bar.ts.date()
            s.add(
                UserDecisionJournal(
                    id=uuid.uuid4(),
                    created_at=datetime(a_date.year, a_date.month, a_date.day),
                    user_id=None,  # the anonymous sample-analyst (NULL) pool
                    instrument_id=inst_id,
                    hypothesis=(
                        f"{_MARKER} {sym} {direction} ({conviction}% conviction) "
                        f"— sample analyst, {a_date.isoformat()}"
                    ),
                    evidence=[],
                    confidence_pct=conviction,
                    predicted_direction=direction,
                    horizon_days=(t_date - a_date).days,
                    threshold_pct=_THRESHOLD_PCT,
                    anchor_price=float(anchor_bar.close),
                    resolved_direction=None,  # OPEN — the engine resolves real moves
                    auto_resolved=False,
                )
            )
        await s.commit()
        early = windows[: n // 2]
        late = windows[n // 2:]
        print(
            f"Seeded {n} OPEN sample-analyst decisions over "
            f"{early[0][2].ts.date()}..{late[-1][2].ts.date()} (NULL pool). "
            f"Conviction is overconfident early (+{_MAX_BIAS}) decaying to measured late; "
            f"direction is blind momentum. Resolve to reveal the real arc."
        )


if __name__ == "__main__":
    asyncio.run(go())
