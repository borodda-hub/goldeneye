from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db.session import get_db
from apps.api.repos import instruments as instr_repo
from apps.api.repos import contracts as contract_repo
from apps.api.repos import price_bars as price_repo
from apps.api.repos import scenarios as scenario_repo
from apps.api.services.model_registry import ForecastContext
from apps.api.services.scenario_engine import run_scenario

router = APIRouter(prefix="/v1/scenarios", tags=["scenarios"])

_FIXTURES_DIR = Path(__file__).resolve().parents[4] / "packages" / "fixtures"


class ShockItem(BaseModel):
    type: str
    region: str | None = None
    delta_temp_f: float | None = None
    delta_bcfd: float | None = None
    delta_bcf: float | None = None
    days: int = 7


class ScenarioRunRequest(BaseModel):
    instrument: str = "NG"
    name: str
    shocks: list[ShockItem]


@router.post("/run")
async def run_scenario_endpoint(
    req: ScenarioRunRequest,
    session: AsyncSession = Depends(get_db),
) -> dict:
    instrument = await instr_repo.get_by_symbol(session, req.instrument)
    if instrument is None:
        raise HTTPException(status_code=404, detail=f"Instrument {req.instrument!r} not found")

    front = await contract_repo.get_front_month(session, instrument.id)
    closes = await price_repo.get_latest_n_closes(
        session, front.id if front else instrument.id, n=100
    )

    baseline_ctx = ForecastContext(symbol=req.instrument, closes=closes)
    shocks_dicts = [s.model_dump(exclude_none=True) for s in req.shocks]

    result = await run_scenario(
        name=req.name,
        instrument=req.instrument,
        shocks=shocks_dicts,
        baseline_ctx=baseline_ctx,
    )

    run = await scenario_repo.create(
        session, instrument_id=instrument.id, name=req.name, shocks=shocks_dicts, result=result
    )
    await session.commit()

    return {
        "run_id": str(run.id),
        "instrument": req.instrument,
        "name": req.name,
        "result": result,
    }


@router.get("/templates")
async def get_templates() -> dict:
    templates_path = _FIXTURES_DIR / "scenario_templates.json"
    if not templates_path.exists():
        return {"templates": []}
    templates = json.loads(templates_path.read_text())
    return {"templates": templates}


@router.get("/runs")
async def list_runs(
    limit: int = 20,
    session: AsyncSession = Depends(get_db),
) -> dict:
    runs = await scenario_repo.get_recent(session, limit=limit)
    return {
        "runs": [
            {
                "run_id": str(r.id),
                "created_at": r.created_at.isoformat(),
                "name": r.name,
                "instrument_id": str(r.instrument_id),
            }
            for r in runs
        ]
    }
