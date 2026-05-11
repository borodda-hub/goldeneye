from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db.session import get_db
from apps.api.repos import alerts as alert_repo
from apps.api.repos import adapter_runs as run_repo

router = APIRouter(prefix="/v1/admin", tags=["admin"])


@router.get("/data-health")
async def data_health(session: AsyncSession = Depends(get_db)) -> dict:
    runs = await run_repo.get_latest_per_adapter(session)
    now = datetime.utcnow()

    adapters = []
    for run in runs:
        lag_minutes: float | None = None
        if run.finished_at:
            lag_minutes = round((now - run.finished_at).total_seconds() / 60, 1)

        adapters.append({
            "name": run.adapter_name,
            "status": run.status,
            "last_success": run.finished_at.isoformat() if run.finished_at else None,
            "lag_minutes": lag_minutes,
            "rows_ingested": run.rows_ingested,
            "error": run.error,
        })

    # If no runs exist, show mock adapters as "ok"
    if not adapters:
        from apps.api.src.settings import settings
        for domain in ("market", "energy", "weather", "positioning", "news"):
            adapters.append({
                "name": f"{domain}.{getattr(settings, f'adapter_{domain}', 'mock')}",
                "status": "ok",
                "last_success": now.isoformat(),
                "lag_minutes": 0,
                "rows_ingested": 0,
                "error": None,
            })

    return {"adapters": adapters}


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
