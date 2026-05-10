"""Load JSON fixture files into a migrated database.

Loads: instruments, contracts, news_events, scenario_runs,
       alerts, journals, paper_trades.
Generated tables (price_bars, eia, cot, weather) are populated by Phase 02 generators.
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path

# Ensure repo root is on sys.path when run as a script
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "packages" / "fixtures"


def _load(name: str) -> list[dict]:
    return json.loads((FIXTURES_DIR / name).read_text())


def _d(s: str | None) -> date | None:
    return date.fromisoformat(s) if s else None


def _dt(s: str | None) -> datetime | None:
    if not s:
        return None
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return dt.replace(tzinfo=None)  # ORM models use TIMESTAMP (no tz); data is all UTC


async def load_all() -> None:
    import uuid as _uuid
    from sqlalchemy import insert, select, Table, MetaData
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from apps.api.db.session import get_session_factory
    from apps.api.db.base import Base
    import apps.api.models.orm.instruments  # noqa: F401 — registers tables
    import apps.api.models.orm.contracts  # noqa: F401
    import apps.api.models.orm.news  # noqa: F401
    import apps.api.models.orm.scenarios  # noqa: F401
    import apps.api.models.orm.alerts  # noqa: F401
    import apps.api.models.orm.journal  # noqa: F401
    import apps.api.models.orm.paper  # noqa: F401

    meta = Base.metadata
    instruments_t = meta.tables["instruments"]
    contracts_t = meta.tables["contracts"]
    news_events_t = meta.tables["news_events"]
    scenario_runs_t = meta.tables["scenario_runs"]
    alerts_t = meta.tables["alerts"]
    journals_t = meta.tables["user_decision_journals"]
    paper_t = meta.tables["paper_trades"]

    async with get_session_factory()() as session:
        async with session.begin():
            # --- instruments ---
            instrument_id_map: dict[str, _uuid.UUID] = {}
            for row in _load("instruments.json"):
                stmt = (
                    pg_insert(instruments_t)
                    .values(
                        symbol=row["symbol"],
                        name=row["name"],
                        exchange=row["exchange"],
                        asset_class=row.get("asset_class", "commodity"),
                        currency=row.get("currency", "USD"),
                        unit=row["unit"],
                        contract_size=row["contract_size"],
                        tick_size=row["tick_size"],
                        metadata=row.get("metadata", {}),
                    )
                    .on_conflict_do_update(
                        index_elements=["symbol"],
                        set_={"name": row["name"]},
                    )
                    .returning(instruments_t.c.id)
                )
                result = await session.execute(stmt)
                instrument_id_map[row["symbol"]] = result.scalar_one()

            # --- contracts ---
            contract_id_map: dict[str, _uuid.UUID] = {}
            for row in _load("contracts.json"):
                instr_id = instrument_id_map[row["instrument_symbol"]]
                stmt = (
                    pg_insert(contracts_t)
                    .values(
                        instrument_id=instr_id,
                        contract_code=row["contract_code"],
                        expiry_date=_d(row["expiry_date"]),
                        is_front_month=row.get("is_front_month", False),
                        metadata={},
                    )
                    .on_conflict_do_update(
                        constraint="uq_contracts_instrument_code",
                        set_={"is_front_month": row.get("is_front_month", False)},
                    )
                    .returning(contracts_t.c.id)
                )
                result = await session.execute(stmt)
                contract_id_map[row["contract_code"]] = result.scalar_one()

            # --- news_events ---
            for row in _load("news_events.json"):
                await session.execute(
                    insert(news_events_t).values(
                        published_at=_dt(row["published_at"]),
                        source=row["source"],
                        headline=row["headline"],
                        body=row.get("body"),
                        category=row.get("category"),
                        sentiment=row.get("sentiment"),
                        impact_score=row.get("impact_score"),
                        affected_regions=row.get("affected_regions") or [],
                        entities=row.get("entities", []),
                        raw={},
                    )
                )

            # --- scenario_runs ---
            for row in _load("scenario_runs.seed.json"):
                instr_id = instrument_id_map[row["instrument_symbol"]]
                await session.execute(
                    insert(scenario_runs_t).values(
                        created_at=_dt(row.get("created_at")),
                        instrument_id=instr_id,
                        name=row["name"],
                        shocks=row["shocks"],
                        result=row["result"],
                    )
                )

            # --- alerts ---
            for row in _load("alerts.seed.json"):
                await session.execute(
                    insert(alerts_t).values(
                        kind=row["kind"],
                        severity=row["severity"],
                        payload=row["payload"],
                        read=row.get("read", False),
                        acknowledged=row.get("acknowledged", False),
                    )
                )

            # --- journals ---
            journal_ids: list[_uuid.UUID] = []
            for row in _load("journals.seed.json"):
                instr_id = instrument_id_map[row["instrument_symbol"]]
                result = await session.execute(
                    insert(journals_t)
                    .values(
                        instrument_id=instr_id,
                        hypothesis=row["hypothesis"],
                        evidence=row.get("evidence", []),
                        confidence_pct=row["confidence_pct"],
                        planned_action=row.get("planned_action"),
                        risk_factors=row.get("risk_factors") or [],
                        invalidation_criteria=row.get("invalidation_criteria"),
                        outcome=row.get("outcome"),
                        reflection=row.get("reflection"),
                        llm_review=row.get("llm_review"),
                    )
                    .returning(journals_t.c.id)
                )
                journal_ids.append(result.scalar_one())

            # --- paper_trades ---
            for row in _load("paper_trades.seed.json"):
                instr_id = instrument_id_map[row["instrument_symbol"]]
                contract_id = contract_id_map.get(row.get("contract_code", ""))
                ref_idx = row.get("journal_ref_index")
                journal_ref = journal_ids[ref_idx] if ref_idx is not None and ref_idx < len(journal_ids) else None
                await session.execute(
                    insert(paper_t).values(
                        opened_at=_dt(row.get("opened_at")),
                        closed_at=_dt(row.get("closed_at")),
                        instrument_id=instr_id,
                        contract_id=contract_id,
                        side=row["side"],
                        size_contracts=row["size_contracts"],
                        entry_price=row["entry_price"],
                        exit_price=row.get("exit_price"),
                        stop_loss=row.get("stop_loss"),
                        take_profit=row.get("take_profit"),
                        status=row.get("status", "open"),
                        rationale=row.get("rationale"),
                        outcome_pnl=row.get("outcome_pnl"),
                        reflection=row.get("reflection"),
                        journal_ref=journal_ref,
                    )
                )


if __name__ == "__main__":
    import asyncio

    asyncio.run(load_all())
    print("load_fixtures: done")
