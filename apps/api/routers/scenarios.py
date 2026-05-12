from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Annotated, Literal, Union

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db.session import get_db
from apps.api.repos import instruments as instr_repo
from apps.api.repos import contracts as contract_repo
from apps.api.repos import price_bars as price_repo
from apps.api.repos import scenarios as scenario_repo
from apps.api.services.model_registry import ForecastContext
from apps.api.services.scenario_engine import run_scenario

router = APIRouter(prefix="/v1/scenarios", tags=["scenarios"])

# Repo layout: apps/api/routers/scenarios.py → parents[3] is the repo root.
# (parents[4] walked one level above, missing packages/fixtures every time.)
_FIXTURES_DIR = Path(__file__).resolve().parents[3] / "packages" / "fixtures"


# ---------------------------------------------------------------------------
# Strict shock discriminated union — see docs/PHASE_06_PLAN.md and
# docs/API_CONTRACTS.md §scenarios. Out-of-bounds values produce 422.
# ---------------------------------------------------------------------------
class WeatherShock(BaseModel):
    type: Literal["weather"]
    region: str = Field(min_length=1, max_length=64)
    delta_temp_f: float = Field(ge=-50, le=50)
    days: int = Field(ge=1, le=60)


class LngExportShock(BaseModel):
    type: Literal["lng_export"]
    delta_bcfd: float = Field(ge=-15, le=15)
    days: int = Field(ge=1, le=60)


class ProductionShock(BaseModel):
    type: Literal["production"]
    delta_bcfd: float = Field(ge=-15, le=15)
    days: int = Field(ge=1, le=60)


class StorageShock(BaseModel):
    type: Literal["storage"]
    delta_bcf: float = Field(ge=-500, le=500)
    days: int = Field(ge=1, le=60)


Shock = Annotated[
    Union[WeatherShock, LngExportShock, ProductionShock, StorageShock],
    Field(discriminator="type"),
]


class ScenarioRunRequest(BaseModel):
    instrument: str = "NG"
    name: str = Field(min_length=1, max_length=200)
    shocks: list[Shock] = Field(min_length=1, max_length=10)


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
    shocks_dicts = [s.model_dump() for s in req.shocks]

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


@router.get("/runs/{run_id}")
async def get_run(
    run_id: str,
    session: AsyncSession = Depends(get_db),
) -> dict:
    try:
        run_uuid = uuid.UUID(run_id)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid run_id format") from exc

    run = await scenario_repo.get_by_id(session, run_uuid)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Scenario run {run_id!r} not found")

    return {
        "run_id": str(run.id),
        "created_at": run.created_at.isoformat(),
        "instrument_id": str(run.instrument_id),
        "name": run.name,
        "shocks": run.shocks,
        "result": run.result,
    }
