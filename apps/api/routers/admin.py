from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db.session import get_db
from apps.api.models.orm.forecasts import ModelForecast
from apps.api.repos import adapter_runs as run_repo
from apps.api.repos import alerts as alert_repo
from apps.api.services.data_health import (
    expected_cadence_minutes,
    rollup_adapter_run,
)
from apps.api.src.settings import settings

router = APIRouter(prefix="/v1/admin", tags=["admin"])

# Env vars whose PRESENCE (never value — per docs/AI_BEHAVIOR.md
# §user_facing_strings_governance) we surface to /admin. The web Admin
# page used to read these via `process.env` in the Next.js server process,
# which never sees the API's .env file. Sourcing them here gives an
# honest answer regardless of where the web bundle runs.
_ENV_VARS_TO_SURFACE: tuple[str, ...] = (
    "DATABASE_URL",
    "REDIS_URL",
    "ANTHROPIC_API_KEY",
    "EIA_API_KEY",
    "LLM_MODE",
    "LLM_MODEL_FAST",
    "LLM_MODEL_SMART",
    "LLM_MODEL_PREMIUM",
    "ADAPTER_MARKET",
    "ADAPTER_ENERGY",
    "ADAPTER_WEATHER",
    "ADAPTER_POSITIONING",
    "ADAPTER_NEWS",
)


def _env_flags() -> dict[str, bool]:
    """Server-side presence check. Empty string counts as unset."""
    return {name: bool(os.environ.get(name)) for name in _ENV_VARS_TO_SURFACE}


@router.get("/data-health")
async def data_health(session: AsyncSession = Depends(get_db)) -> dict:
    """Adapter and model rollups."""
    now = datetime.utcnow()
    runs = await run_repo.get_latest_per_adapter(session)

    adapters = [rollup_adapter_run(run, now=now) for run in runs]

    # Mock fallback when no adapter_runs exist yet
    if not adapters:
        for domain in ("market", "energy", "weather", "positioning", "news"):
            adapter = getattr(settings, f"adapter_{domain}", "mock")
            name = f"{domain}.{adapter}"
            adapters.append({
                "name": name,
                "status": "ok",
                "last_success": now.isoformat(),
                "lag_minutes": 0.0,
                "rows_ingested": 0,
                "error": None,
                "expected_cadence_minutes": expected_cadence_minutes(name),
            })

    # Model rollup: count forecasts per model in last 7 days, get most recent generated_at
    seven_days_ago = now - timedelta(days=7)
    model_q = (
        select(
            ModelForecast.model_name,
            func.max(ModelForecast.generated_at).label("last_generated"),
            func.count(ModelForecast.id).label("sample_count_7d"),
        )
        .where(ModelForecast.generated_at >= seven_days_ago)
        .group_by(ModelForecast.model_name)
    )
    model_rows = (await session.execute(model_q)).all()
    models = [
        {
            "name": row.model_name,
            "last_forecast_at": row.last_generated.isoformat() if row.last_generated else None,
            "sample_count_7d": int(row.sample_count_7d),
        }
        for row in model_rows
    ]

    return {
        "adapters": adapters,
        "models": models,
        "env_flags": _env_flags(),
    }


@router.get("/alerts")
async def list_alerts(
    unread: bool = Query(default=False),
    limit: int = Query(default=50, le=500),
    session: AsyncSession = Depends(get_db),
) -> dict:
    if unread:
        alerts = await alert_repo.get_unread(session, limit=limit)
    else:
        alerts = await alert_repo.get_all(session, limit=limit)

    return {
        "alerts": [
            {
                "id": str(a.id),
                "created_at": a.created_at.isoformat(),
                "kind": a.kind,
                "severity": a.severity,
                "payload": a.payload,
                "read": a.read,
                "acknowledged": a.acknowledged,
            }
            for a in alerts
        ]
    }


@router.post("/alerts/{alert_id}/ack")
async def acknowledge_alert(
    alert_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> dict:
    alert = await alert_repo.get_by_id(session, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert = await alert_repo.acknowledge(session, alert)
    await session.commit()
    return {"id": str(alert.id), "acknowledged": True}
