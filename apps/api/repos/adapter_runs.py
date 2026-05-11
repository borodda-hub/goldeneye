from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.orm.adapter_runs import AdapterRun


async def get_latest_per_adapter(session: AsyncSession) -> list[AdapterRun]:
    """Return the most recent run row for each distinct adapter_name."""
    # Subquery: max started_at per adapter_name
    from sqlalchemy import func, text

    subq = (
        select(AdapterRun.adapter_name, func.max(AdapterRun.started_at).label("max_started"))
        .group_by(AdapterRun.adapter_name)
        .subquery()
    )
    result = await session.execute(
        select(AdapterRun).join(
            subq,
            (AdapterRun.adapter_name == subq.c.adapter_name)
            & (AdapterRun.started_at == subq.c.max_started),
        )
    )
    return list(result.scalars().all())
