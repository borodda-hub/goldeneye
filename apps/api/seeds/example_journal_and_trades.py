"""Seed three example journal entries and three closed paper trades so the
demo's Journal and Paper Trading screens have content on first load.

The journal entries carry pre-generated `llm_review` blobs in the shape
the explainer service produces (text + safety envelope dict). The paper
trades are linked to the journal entries via `journal_ref` and represent
realistic open→close round trips with non-trivial PnL outcomes (one win,
one loss, one break-even-ish).

Idempotent: if rows already exist for any of the example hypotheses,
this module is a no-op. Safe to re-run.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

# NG tick value — matches services/paper_engine.py:
# (exit - entry) × size × 10,000 USD/MMBtu.
NG_TICK_VALUE_USD = 10_000.0


def _now() -> datetime:
    return datetime.utcnow()


def _example_journal_rows(instrument_id: uuid.UUID) -> list[dict[str, Any]]:
    """Three realistic decision-journal entries with pre-generated LLM reviews."""
    now = _now()
    return [
        {
            "id": uuid.uuid4(),
            "created_at": now - timedelta(days=14),
            "user_id": None,
            "instrument_id": instrument_id,
            "hypothesis": (
                "Cold snap not yet priced in; expect a 3-5% rally in NGM26 over "
                "the next 2 weeks as Northeast HDDs come in well above the 5-year "
                "average."
            ),
            "evidence": [
                {"source": "NWS 6-10 day temp anomaly map", "summary": "Strong negative anomaly across Northeast", "weight": 0.5},
                {"source": "EIA weekly storage (last)", "summary": "Build of +12 Bcf vs +28 consensus", "weight": 0.3},
                {"source": "COT disaggregated", "summary": "Managed-money net long up ~18k WoW", "weight": 0.2},
            ],
            "confidence_pct": 65,
            "planned_action": "Paper-long 2 NGM26 contracts if storage delta surprises smaller than -10 Bcf.",
            "risk_factors": [
                "Above-normal storage cushion ~140 Bcf vs 5y avg",
                "Crowded long positioning per latest COT",
            ],
            "invalidation_criteria": "Front-month closes below 3.20 within 5 trading days, or NWS 8-14 day map flips warm.",
            "outcome": "win",
            "reflection": "Cold snap held; closed long for +4.1% over 9 trading days.",
            "llm_review": {
                "text": (
                    "Implicit assumption: the hypothesis assumes that the storage cushion "
                    "is the dominant counter-pressure, without quantifying how much of the "
                    "weather upside is already in forward curves.\n"
                    "Strengthening evidence: a basis differential check at Algonquin or Transco "
                    "Zone 6 would test whether Northeast demand pull is being priced regionally.\n"
                    "Missing risk: LNG export pace is not addressed — any feedgas step-down would "
                    "partially offset the cold-snap pull.\n"
                    "Invalidation: specific, time-bound, testable; passes the decision-quality bar.\n"
                    "Confidence assessment: 65% reads as consistent with the evidence weight given "
                    "two corroborating data points and one cautionary positioning input.\n"
                    "Process improvement: add a re-evaluation trigger date (e.g., day 7) in addition "
                    "to the price-level invalidation."
                ),
                "safety": {
                    "confidence": "medium",
                    "caveats": [
                        "This review assesses decision quality only, not the merits of any specific position.",
                    ],
                    "as_of": (now - timedelta(days=14)).isoformat(),
                },
            },
        },
        {
            "id": uuid.uuid4(),
            "created_at": now - timedelta(days=7),
            "user_id": None,
            "instrument_id": instrument_id,
            "hypothesis": (
                "Production freeze-off risk overblown; expect a -2 to -3% fade in NGM26 "
                "as bottom-of-range weather forecasts moderate."
            ),
            "evidence": [
                {"source": "NWS 8-14 day map", "summary": "Warming trend across Midcontinent", "weight": 0.6},
                {"source": "Daily production estimates", "summary": "Lower-48 prod recovering, freeze-offs declining", "weight": 0.4},
            ],
            "confidence_pct": 55,
            "planned_action": "Paper-short 1 NGM26 contract; tight stop above 3.55.",
            "risk_factors": [
                "Tail risk of a late-season Arctic re-entry",
                "Crowded short positioning could squeeze on any cold-headline pop",
            ],
            "invalidation_criteria": "Front-month closes above 3.55 within 3 trading days.",
            "outcome": "loss",
            "reflection": "Stopped out on a single-day +3.7% pop after an unexpected EIA storage surprise.",
            "llm_review": {
                "text": (
                    "Implicit assumption: the hypothesis treats weather moderation as already "
                    "priced, without testing whether the curve's contango steepening reflects that.\n"
                    "Strengthening evidence: a pipeline-flow data point (Northeast → Gulf, or "
                    "Henry Hub interruptible nominations) would test the production-recovery thesis "
                    "harder.\n"
                    "Missing risk: an EIA storage print surprise is not addressed in the invalidation "
                    "criteria — only price-based.\n"
                    "Invalidation: testable but the 3-day window may be too short for a weekly "
                    "weather-driven thesis.\n"
                    "Confidence assessment: 55% appears modestly elevated given only two "
                    "data points and crowded-short positioning.\n"
                    "Process improvement: consider a non-price invalidation criterion (e.g., "
                    "if EIA prints > +35 Bcf surprise, exit regardless of level)."
                ),
                "safety": {
                    "confidence": "medium",
                    "caveats": [
                        "This review assesses decision quality only, not the merits of any specific position.",
                    ],
                    "as_of": (now - timedelta(days=7)).isoformat(),
                },
            },
        },
        {
            "id": uuid.uuid4(),
            "created_at": now - timedelta(days=2),
            "user_id": None,
            "instrument_id": instrument_id,
            "hypothesis": (
                "Mean-reversion setup: NGM26 has overshot the 20-day mean by ~2 stdev "
                "on weather-driven flows; expect a fade back to the band over 5 sessions."
            ),
            "evidence": [
                {"source": "Bollinger Band (20d, 2σ)", "summary": "Last close 1.8σ above upper band", "weight": 0.5},
                {"source": "RSI-14", "summary": "RSI at 71 — overbought zone", "weight": 0.3},
                {"source": "Front-2nd basis", "summary": "Steepening contango, no urgency in prompt", "weight": 0.2},
            ],
            "confidence_pct": 50,
            "planned_action": "Paper-short 1 NGM26 with stop at +0.5σ further extension.",
            "risk_factors": [
                "Mean reversion fails in trending regimes; vol regime currently reads elevated",
                "Weather forecast revisions could push the move further before fade",
            ],
            "invalidation_criteria": "Front-month makes a new high vs the entry; or holds above the upper band for 3 consecutive sessions.",
            "outcome": None,  # Still open / pending in the example.
            "reflection": None,
            "llm_review": {
                "text": (
                    "Implicit assumption: the hypothesis assumes mean-reversion regime conditions "
                    "without verifying which volatility regime the model currently classifies.\n"
                    "Strengthening evidence: a check of historical 2σ extensions in similar "
                    "vol regimes — does mean reversion or trend-continuation win more often?\n"
                    "Missing risk: the elevated-regime risk factor is acknowledged but not "
                    "quantified — at what regime probability does the setup invalidate?\n"
                    "Invalidation: clear and time-bound — both a price condition and a "
                    "duration condition, which is stronger than either alone.\n"
                    "Confidence assessment: 50% reads as appropriately humble for a counter-trend "
                    "setup in an elevated-vol regime.\n"
                    "Process improvement: log the volatility regime explicitly at entry so the "
                    "post-mortem can attribute outcome to setup vs regime fit."
                ),
                "safety": {
                    "confidence": "medium",
                    "caveats": [
                        "This review assesses decision quality only, not the merits of any specific position.",
                    ],
                    "as_of": (now - timedelta(days=2)).isoformat(),
                },
            },
        },
    ]


def _example_paper_trade_rows(
    instrument_id: uuid.UUID,
    contract_id: uuid.UUID | None,
    journal_ids: list[uuid.UUID],
) -> list[dict[str, Any]]:
    """Three paper trades. First two are closed (one win, one loss), third is open."""
    now = _now()

    def _pnl(side: str, size: float, entry: float, exit_: float) -> float:
        sign = 1.0 if side == "long" else -1.0
        return round(sign * (exit_ - entry) * size * NG_TICK_VALUE_USD, 2)

    rows: list[dict[str, Any]] = []

    # Trade 1 — winning long, paired to journal entry #1.
    entry, exit_, size = 3.18, 3.31, 2.0
    rows.append(
        {
            "id": uuid.uuid4(),
            "opened_at": now - timedelta(days=13),
            "closed_at": now - timedelta(days=4),
            "user_id": None,
            "instrument_id": instrument_id,
            "contract_id": contract_id,
            "side": "long",
            "size_contracts": size,
            "entry_price": entry,
            "exit_price": exit_,
            "stop_loss": 3.05,
            "take_profit": 3.45,
            "status": "closed",
            "rationale": "Cold snap rally setup; paired to journal #1.",
            "outcome_pnl": _pnl("long", size, entry, exit_),
            "reflection": "Thesis played out within window; exited at +4.1% target zone.",
            "journal_ref": journal_ids[0] if journal_ids else None,
        }
    )

    # Trade 2 — losing short, paired to journal entry #2.
    entry, exit_, size = 3.42, 3.56, 1.0
    rows.append(
        {
            "id": uuid.uuid4(),
            "opened_at": now - timedelta(days=6),
            "closed_at": now - timedelta(days=5),
            "user_id": None,
            "instrument_id": instrument_id,
            "contract_id": contract_id,
            "side": "short",
            "size_contracts": size,
            "entry_price": entry,
            "exit_price": exit_,
            "stop_loss": 3.55,
            "take_profit": 3.32,
            "status": "closed",
            "rationale": "Production-recovery fade; paired to journal #2.",
            "outcome_pnl": _pnl("short", size, entry, exit_),
            "reflection": "Stop hit on EIA storage surprise. Lesson logged in journal reflection.",
            "journal_ref": journal_ids[1] if len(journal_ids) > 1 else None,
        }
    )

    # Trade 3 — open short, paired to journal entry #3.
    rows.append(
        {
            "id": uuid.uuid4(),
            "opened_at": now - timedelta(days=1),
            "closed_at": None,
            "user_id": None,
            "instrument_id": instrument_id,
            "contract_id": contract_id,
            "side": "short",
            "size_contracts": 1.0,
            "entry_price": 3.48,
            "exit_price": None,
            "stop_loss": 3.58,
            "take_profit": 3.32,
            "status": "open",
            "rationale": "Mean-reversion fade; paired to journal #3.",
            "outcome_pnl": None,
            "reflection": None,
            "journal_ref": journal_ids[2] if len(journal_ids) > 2 else None,
        }
    )

    return rows


_IDEMPOTENCY_MARKER = "Cold snap not yet priced in; expect a 3-5% rally in NGM26"


async def seed_examples(session: AsyncSession) -> tuple[int, int]:
    """Insert example journal + paper-trade rows if not already present.

    Returns (journal_count, trade_count) inserted (0/0 if idempotent skip).
    """
    from apps.api.db.base import Base

    meta = Base.metadata
    journal_t = meta.tables["user_decision_journals"]
    trades_t = meta.tables["paper_trades"]
    instruments_t = meta.tables["instruments"]
    contracts_t = meta.tables["contracts"]

    # Idempotency: skip if any of our example hypotheses already exist.
    existing = await session.execute(
        select(journal_t.c.id).where(journal_t.c.hypothesis.like(f"{_IDEMPOTENCY_MARKER}%"))
    )
    if existing.first() is not None:
        return (0, 0)

    # Resolve the NG instrument id and current front-month contract id.
    ng_row = (
        await session.execute(select(instruments_t).where(instruments_t.c.symbol == "NG"))
    ).first()
    if ng_row is None:
        raise RuntimeError("seed_examples: NG instrument not found — load fixtures first")
    instrument_id = ng_row.id

    contract_row = (
        await session.execute(
            select(contracts_t)
            .where(contracts_t.c.contract_code == "NGM26")
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
