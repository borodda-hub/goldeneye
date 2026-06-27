from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.auth.deps import get_optional_user
from apps.api.db.session import get_db
from apps.api.models.orm.users import User
from apps.api.repos import contracts as contract_repo
from apps.api.repos import instruments as instr_repo
from apps.api.repos import journal as journal_repo
from apps.api.repos import scenarios as scenario_repo
from apps.api.services.ensemble import compute_ensemble
from apps.api.services.llm_explainer import (
    explain_signal,
    narrate_scenario,
    review_journal_entry,
    summarize_market,
)
from apps.api.services.model_calibration import model_weights_for
from apps.api.services.model_registry import ForecastContext, run_all
from apps.api.services.price_lookup import get_latest_closes

router = APIRouter(prefix="/v1/explain", tags=["explain"])


class MarketExplainRequest(BaseModel):
    ctx: dict = {}  # type: ignore[type-arg]


class SignalExplainRequest(BaseModel):
    signal_id: str | None = None
    symbol: str = "NG"


class ScenarioExplainRequest(BaseModel):
    run_id: uuid.UUID


class JournalExplainRequest(BaseModel):
    entry_id: uuid.UUID


@router.post("/market")
async def explain_market(
    req: MarketExplainRequest,
    session: AsyncSession = Depends(get_db),
) -> dict:
    text, safety = await summarize_market(req.ctx)
    return {"text": text, "safety": safety.model_dump()}


@router.post("/signal")
async def explain_signal_endpoint(
    req: SignalExplainRequest,
    session: AsyncSession = Depends(get_db),
) -> dict:
    instrument = await instr_repo.get_by_symbol(session, req.symbol)
    if instrument is None:
        raise HTTPException(status_code=404, detail=f"Instrument {req.symbol!r} not found")

    front = await contract_repo.get_front_month(session, instrument.id)
    closes = await get_latest_closes(
        session,
        contract_id=front.id if front else None,
        contract_code=front.contract_code if front else None,
        n=100,
    )
    ctx = ForecastContext(
        symbol=req.symbol,
        closes=closes,
        asset_class=getattr(instrument, "asset_class", "commodity"),
    )
    results = await run_all(ctx)
    weights = await model_weights_for(session, instrument.id, "1d")
    ensemble = compute_ensemble(results, model_weights=weights)

    signal = {
        "direction": ensemble["direction"],
        "confidence": ensemble["confidence"],
        "vol_regime": ensemble.get("vol_regime"),
    }
    text, safety = await explain_signal(signal, {"symbol": req.symbol})
    return {"text": text, "safety": safety.model_dump()}


@router.post("/scenario")
async def explain_scenario(
    req: ScenarioExplainRequest,
    session: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_optional_user),
) -> dict:
    scope = user.id if user else None
    run = await scenario_repo.get_by_id(session, req.run_id)
    if run is None or run.user_id != scope:
        raise HTTPException(status_code=404, detail="Scenario run not found")

    result = run.result or {}
    ctx: dict = {"instrument": str(run.instrument_id)}  # type: ignore[type-arg]
    text, safety = await narrate_scenario({"name": run.name, "shocks": run.shocks}, result, ctx)
    return {"text": text, "safety": safety.model_dump()}


@router.post("/journal")
async def explain_journal(
    req: JournalExplainRequest,
    session: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_optional_user),
) -> dict:
    scope = user.id if user else None
    entry = await journal_repo.get_by_id(session, req.entry_id)
    if entry is None or entry.user_id != scope:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    entry_dict = {
        "hypothesis": entry.hypothesis,
        "evidence": entry.evidence,
        "confidence_pct": entry.confidence_pct,
        "planned_action": entry.planned_action,
        "risk_factors": entry.risk_factors,
        "invalidation_criteria": entry.invalidation_criteria,
    }
    text, safety = await review_journal_entry(entry_dict)
    return {"text": text, "safety": safety.model_dump()}
