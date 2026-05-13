"""CL-flavored example journal entries + paper trades.

Mirrors the NG seed in example_journal_and_trades.py but with crude-oil
hypotheses (OPEC/refinery margins/Cushing/SPR). Three journal entries +
three paper trades, two closed and one open, paired by journal_ref.

Idempotent: skips when the CL marker hypothesis already exists.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

# WTI tick value: (exit - entry) × size × $1,000/contract (NYMEX CL).
CL_TICK_VALUE_USD = 1_000.0


def _now() -> datetime:
    return datetime.utcnow()


def _example_journal_rows(instrument_id: uuid.UUID) -> list[dict[str, Any]]:
    now = _now()
    return [
        {
            "id": uuid.uuid4(),
            "created_at": now - timedelta(days=12),
            "user_id": None,
            "instrument_id": instrument_id,
            "hypothesis": (
                "OPEC+ compliance is tightening into Q3; expect a +4-6% rally "
                "in CLN26 over the next 10 trading days as physical premiums "
                "expand on tighter Saudi/UAE shipments."
            ),
            "evidence": [
                {"source": "Reuters OPEC+ shipment tracker", "summary": "Saudi exports -350 kb/d MoM in current month", "weight": 0.45},
                {"source": "EIA Weekly Petroleum Status (last)", "summary": "Cushing crude stocks drew 1.8 mbbl vs 0.4 consensus", "weight": 0.35},
                {"source": "CFTC managed-money net long", "summary": "Net long +28k contracts WoW", "weight": 0.20},
            ],
            "confidence_pct": 70,
            "planned_action": "Paper-long 2 CLN26 contracts if Cushing draws confirm in tomorrow's EIA print.",
            "risk_factors": [
                "Demand-side softness: gasoline crack spreads have been flat",
                "Crowded long positioning per latest COT",
                "Iran headline risk could whipsaw both directions",
            ],
            "invalidation_criteria": "Front-month closes below $82.00 within 5 trading days, or Cushing builds back > 1 mbbl on next EIA print.",
            "outcome": "win",
            "reflection": "OPEC narrative held; closed long for +4.8% over 8 sessions.",
            "llm_review": {
                "text": (
                    "Implicit assumption: the hypothesis treats OPEC compliance as the dominant "
                    "driver without quantifying how much of the production cut is already in forward curves.\n"
                    "Strengthening evidence: a Brent-WTI spread check would test whether the tightening "
                    "is global vs WTI-specific.\n"
                    "Missing risk: refinery turnaround season is not addressed — demand softness "
                    "from spring maintenance could partially offset the supply-side pull.\n"
                    "Invalidation: specific, dual-condition (price + inventory), and time-bound. Strong.\n"
                    "Confidence assessment: 70% appears moderately elevated given three supportive "
                    "data points and crowded long positioning.\n"
                    "Process improvement: log the Brent-WTI spread at entry as an attribution variable."
                ),
                "safety": {
                    "confidence": "medium",
                    "caveats": [
                        "This review assesses decision quality only, not the merits of any specific position.",
                    ],
                    "as_of": (now - timedelta(days=12)).isoformat(),
                },
            },
        },
        {
            "id": uuid.uuid4(),
            "created_at": now - timedelta(days=6),
            "user_id": None,
            "instrument_id": instrument_id,
            "hypothesis": (
                "Refinery utilization is rolling over heading into summer maintenance; "
                "expect a 2-3% fade in CLN26 as gasoline demand reads softer than 5-year average."
            ),
            "evidence": [
                {"source": "EIA Weekly — refinery utilization", "summary": "Down 1.4 pp vs same week last year", "weight": 0.50},
                {"source": "Gasoline crack spread", "summary": "$22/bbl, below 5y same-week median", "weight": 0.30},
                {"source": "EIA distillate stocks", "summary": "Build of 2.1 mbbl, above consensus", "weight": 0.20},
            ],
            "confidence_pct": 55,
            "planned_action": "Paper-short 1 CLN26 contract; tight stop above $94.00.",
            "risk_factors": [
                "Geopolitical headline risk could squeeze short into pop",
                "EIA prints have been noisy quarter-end",
            ],
            "invalidation_criteria": "Front-month closes above $94.00 within 3 trading days.",
            "outcome": "loss",
            "reflection": "Stopped out on a Middle East headline pop; signal was correct but timing wrong.",
            "llm_review": {
                "text": (
                    "Implicit assumption: refinery utilization weakness is treated as enduring, but "
                    "spring maintenance is seasonal and may already be priced.\n"
                    "Strengthening evidence: a check on cracking margins at the Gulf Coast vs Midwest "
                    "would test whether the weakness is regional or systemic.\n"
                    "Missing risk: geopolitical premia in crude can decouple from refining margins "
                    "entirely — the invalidation acknowledges price but not the catalyst.\n"
                    "Invalidation: testable but the 3-day window may be too short for a fundamentals-"
                    "driven thesis.\n"
                    "Confidence assessment: 55% reads as appropriately humble given mixed signals.\n"
                    "Process improvement: consider sizing down further in elevated-geopolitical-risk "
                    "environments rather than tightening stops."
                ),
                "safety": {
                    "confidence": "medium",
                    "caveats": [
                        "This review assesses decision quality only, not the merits of any specific position.",
                    ],
                    "as_of": (now - timedelta(days=6)).isoformat(),
                },
            },
        },
        {
            "id": uuid.uuid4(),
            "created_at": now - timedelta(days=1),
            "user_id": None,
            "instrument_id": instrument_id,
            "hypothesis": (
                "Cushing OK stocks at 5-year seasonal low; physical premiums in Midland "
                "and Mars are firming. Expect a 1-2% grind higher in CLN26 over the next "
                "5 sessions as the WTI delivery point tightens."
            ),
            "evidence": [
                {"source": "EIA Weekly — Cushing stocks", "summary": "Drew to 22.5 mbbl, 8 mbbl below 5y avg", "weight": 0.55},
                {"source": "Argus Midland differential", "summary": "Flat to WTI vs -$1.20 last month", "weight": 0.30},
                {"source": "EIA total ex-SPR stocks", "summary": "Flat WoW; no broader build pressure", "weight": 0.15},
            ],
            "confidence_pct": 60,
            "planned_action": "Paper-long 1 CLN26 with stop at -1% from entry.",
            "risk_factors": [
                "SPR release headline risk could flood Cushing region",
                "Cushing is technical/local — broader Brent weakness could overwhelm",
            ],
            "invalidation_criteria": "Front-month closes below entry - 1% within 3 sessions, or Cushing prints a build > 1 mbbl on next EIA report.",
            "outcome": None,  # Still open in the example.
            "reflection": None,
            "llm_review": {
                "text": (
                    "Implicit assumption: the hypothesis treats Cushing as the marginal WTI driver, "
                    "but global crude flows can dominate when geopolitical premia spike.\n"
                    "Strengthening evidence: rail/pipeline-flow data into and out of PADD 2 would "
                    "test whether the Cushing draw is sustainable.\n"
                    "Missing risk: SPR release timing is acknowledged as a risk but not quantified — "
                    "what SPR announcement would invalidate?\n"
                    "Invalidation: dual-condition (price + EIA print) is stronger than price-only.\n"
                    "Confidence assessment: 60% reads as appropriately calibrated for a technical "
                    "delivery-point thesis in an uncertain macro regime.\n"
                    "Process improvement: log the Brent-WTI spread at entry — Cushing-driven theses "
                    "tend to compress the spread, which is a useful attribution check."
                ),
                "safety": {
                    "confidence": "medium",
                    "caveats": [
                        "This review assesses decision quality only, not the merits of any specific position.",
                    ],
                    "as_of": (now - timedelta(days=1)).isoformat(),
                },
            },
        },
    ]


def _example_paper_trade_rows(
    instrument_id: uuid.UUID,
    contract_id: uuid.UUID | None,
    journal_ids: list[uuid.UUID],
) -> list[dict[str, Any]]:
    now = _now()

    def _pnl(side: str, size: float, entry: float, exit_: float) -> float:
        sign = 1.0 if side == "long" else -1.0
        return round(sign * (exit_ - entry) * size * CL_TICK_VALUE_USD, 2)

    rows: list[dict[str, Any]] = []

    # Trade 1 — winning long, paired to journal entry #1.
    entry, exit_, size = 84.20, 88.25, 2.0
    rows.append(
        {
            "id": uuid.uuid4(),
            "opened_at": now - timedelta(days=11),
            "closed_at": now - timedelta(days=3),
            "user_id": None,
            "instrument_id": instrument_id,
            "contract_id": contract_id,
            "side": "long",
            "size_contracts": size,
            "entry_price": entry,
            "exit_price": exit_,
            "stop_loss": 82.00,
            "take_profit": 89.00,
            "status": "closed",
            "rationale": "OPEC compliance rally; paired to journal #1.",
            "outcome_pnl": _pnl("long", size, entry, exit_),
            "reflection": "Thesis played out; exited near +4.8% target.",
            "journal_ref": journal_ids[0] if journal_ids else None,
        }
    )

    # Trade 2 — losing short, paired to journal entry #2.
    entry, exit_, size = 91.50, 94.10, 1.0
    rows.append(
        {
            "id": uuid.uuid4(),
            "opened_at": now - timedelta(days=5),
            "closed_at": now - timedelta(days=4),
            "user_id": None,
            "instrument_id": instrument_id,
            "contract_id": contract_id,
            "side": "short",
            "size_contracts": size,
            "entry_price": entry,
            "exit_price": exit_,
            "stop_loss": 94.00,
            "take_profit": 89.50,
            "status": "closed",
            "rationale": "Refinery-margin fade; paired to journal #2.",
            "outcome_pnl": _pnl("short", size, entry, exit_),
            "reflection": "Stopped out on a Middle East headline pop. Geopolitical risk underweighted.",
            "journal_ref": journal_ids[1] if len(journal_ids) > 1 else None,
        }
    )

    # Trade 3 — open long, paired to journal entry #3.
    rows.append(
        {
            "id": uuid.uuid4(),
            "opened_at": now - timedelta(hours=18),
            "closed_at": None,
            "user_id": None,
            "instrument_id": instrument_id,
            "contract_id": contract_id,
            "side": "long",
            "size_contracts": 1.0,
            "entry_price": 100.20,
            "exit_price": None,
            "stop_loss": 99.20,
            "take_profit": 102.50,
            "status": "open",
            "rationale": "Cushing tightening; paired to journal #3.",
            "outcome_pnl": None,
            "reflection": None,
            "journal_ref": journal_ids[2] if len(journal_ids) > 2 else None,
        }
    )

    return rows


_IDEMPOTENCY_MARKER = "OPEC+ compliance is tightening into Q3"


async def seed_cl_examples(session: AsyncSession) -> tuple[int, int]:
    """Insert CL example journal + paper-trade rows. Idempotent."""
    from apps.api.db.base import Base

    meta = Base.metadata
    journal_t = meta.tables["user_decision_journals"]
    trades_t = meta.tables["paper_trades"]
    instruments_t = meta.tables["instruments"]
    contracts_t = meta.tables["contracts"]

    existing = await session.execute(
        select(journal_t.c.id).where(
            journal_t.c.hypothesis.like(f"{_IDEMPOTENCY_MARKER}%")
        )
    )
    if existing.first() is not None:
        return (0, 0)

    cl_row = (
        await session.execute(
            select(instruments_t).where(instruments_t.c.symbol == "CL")
        )
    ).first()
    if cl_row is None:
        raise RuntimeError(
            "seed_cl_examples: CL instrument not found — run load_fixtures first"
        )
    instrument_id = cl_row.id

    contract_row = (
        await session.execute(
            select(contracts_t)
            .where(contracts_t.c.contract_code == "CLN26")
            .limit(1)
        )
    ).first()
    contract_id = contract_row.id if contract_row is not None else None

    journal_rows = _example_journal_rows(instrument_id)
    await session.execute(insert(journal_t).values(journal_rows))

    journal_ids = [r["id"] for r in journal_rows]
    trade_rows = _example_paper_trade_rows(instrument_id, contract_id, journal_ids)
    await session.execute(insert(trades_t).values(trade_rows))

    return (len(journal_rows), len(trade_rows))


if __name__ == "__main__":
    """Convenience runner: python -m apps.api.seeds.example_cl_journal_and_trades"""
    import asyncio
    import sys
    from pathlib import Path

    _REPO_ROOT = Path(__file__).resolve().parents[3]
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))

    async def go() -> None:
        from apps.api.db.session import get_session_factory
        import apps.api.models.orm.instruments  # noqa: F401
        import apps.api.models.orm.contracts  # noqa: F401
        import apps.api.models.orm.journal  # noqa: F401
        import apps.api.models.orm.paper  # noqa: F401

        async with get_session_factory()() as session:
            async with session.begin():
                j, t = await seed_cl_examples(session)
                print(f"inserted {j} CL journal rows + {t} paper-trade rows")

    asyncio.run(go())
