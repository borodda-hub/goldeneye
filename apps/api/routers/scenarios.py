from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.auth.deps import get_optional_user
from apps.api.db.session import get_db
from apps.api.models.orm.users import User
from apps.api.repos import contracts as contract_repo
from apps.api.repos import instruments as instr_repo
from apps.api.repos import scenarios as scenario_repo
from apps.api.services.model_calibration import model_weights_for
from apps.api.services.model_registry import ForecastContext
from apps.api.services.price_lookup import get_latest_closes
from apps.api.services.scenario_engine import run_scenario
from apps.api.services.scenario_pdf import render_scenario_pdf

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


# --- Crude oil (Brent / WTI) shock taxonomy ---------------------------------
# Real oil-market units: million barrels/day for flows, million barrels for
# stocks. Directionality matches the lean layer in apps/web/lib/scenarioLean.ts.
class OpecSupplyShock(BaseModel):
    type: Literal["opec_supply"]
    delta_mbpd: float = Field(ge=-10, le=10)  # OPEC+ output change (cut < 0)
    days: int = Field(ge=1, le=180)


class GeopoliticalSupplyShock(BaseModel):
    type: Literal["geopolitical_supply"]
    region: str = Field(min_length=1, max_length=64)  # hormuz, russia, mideast, libya
    delta_mbpd: float = Field(ge=-25, le=25)  # supply removed from market (outage < 0)
    days: int = Field(ge=1, le=180)


class DemandShock(BaseModel):
    type: Literal["demand"]
    region: str = Field(min_length=1, max_length=64)  # china, oecd, global
    delta_mbpd: float = Field(ge=-15, le=15)  # demand change (more demand > 0)
    days: int = Field(ge=1, le=180)


class InventoryShock(BaseModel):
    type: Literal["inventory"]
    delta_mmbbl: float = Field(ge=-300, le=300)  # available stocks (build / SPR release > 0)
    days: int = Field(ge=1, le=180)


Shock = Annotated[
    WeatherShock
    | LngExportShock
    | ProductionShock
    | StorageShock
    | OpecSupplyShock
    | GeopoliticalSupplyShock
    | DemandShock
    | InventoryShock,
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
    user: User | None = Depends(get_optional_user),
) -> dict:
    scope = user.id if user else None
    instrument = await instr_repo.get_by_symbol(session, req.instrument)
    if instrument is None:
        raise HTTPException(status_code=404, detail=f"Instrument {req.instrument!r} not found")

    front = await contract_repo.get_front_month(session, instrument.id)
    closes = await get_latest_closes(
        session,
        contract_id=front.id if front else None,
        contract_code=front.contract_code if front else None,
        n=100,
    )

    baseline_ctx = ForecastContext(symbol=req.instrument, closes=closes)
    shocks_dicts = [s.model_dump() for s in req.shocks]
    weights = await model_weights_for(session, instrument.id, "1d")

    result = await run_scenario(
        name=req.name,
        instrument=req.instrument,
        shocks=shocks_dicts,
        baseline_ctx=baseline_ctx,
        model_weights=weights,
    )

    run = await scenario_repo.create(
        session, instrument_id=instrument.id, name=req.name, shocks=shocks_dicts,
        result=result, user_id=scope,
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
    templates = json.loads(templates_path.read_text(encoding="utf-8"))
    return {"templates": templates}


@router.get("/runs")
async def list_runs(
    limit: int = 20,
    session: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_optional_user),
) -> dict:
    runs = await scenario_repo.get_recent(
        session, limit=limit, user_id=(user.id if user else None)
    )
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
    user: User | None = Depends(get_optional_user),
) -> dict:
    scope = user.id if user else None
    try:
        run_uuid = uuid.UUID(run_id)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid run_id format") from exc

    run = await scenario_repo.get_by_id(session, run_uuid)
    if run is None or run.user_id != scope:
        raise HTTPException(status_code=404, detail=f"Scenario run {run_id!r} not found")

    return {
        "run_id": str(run.id),
        "created_at": run.created_at.isoformat(),
        "instrument_id": str(run.instrument_id),
        "name": run.name,
        "shocks": run.shocks,
        "result": run.result,
    }


@router.get("/runs/{run_id}/export.pdf")
async def export_run_pdf(
    run_id: str,
    session: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_optional_user),
) -> Response:
    """Render a scenario run as an executive PDF report (download)."""
    scope = user.id if user else None
    try:
        run_uuid = uuid.UUID(run_id)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid run_id format") from exc

    run = await scenario_repo.get_by_id(session, run_uuid)
    if run is None or run.user_id != scope:
        raise HTTPException(status_code=404, detail=f"Scenario run {run_id!r} not found")

    pdf_bytes = render_scenario_pdf(
        {
            "run_id": str(run.id),
            "created_at": run.created_at.isoformat(),
            "name": run.name,
            "shocks": run.shocks or [],
            "result": run.result or {},
        }
    )

    # Filename: stable per-run, lower-case slug fragment + short UUID prefix.
    slug = "".join(c if c.isalnum() else "-" for c in (run.name or "scenario").lower())
    slug = "-".join(filter(None, slug.split("-")))[:50] or "scenario"
    filename = f"ngti-scenario-{slug}-{str(run.id)[:8]}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
