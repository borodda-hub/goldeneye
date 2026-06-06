"""Repository for accounts — user upsert + per-user settings."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.models.orm.users import User, UserSettings


async def upsert(
    session: AsyncSession, *, clerk_user_id: str, email: str | None = None
) -> User:
    """Insert-or-touch the user for this Clerk id, bumping last_seen_at."""
    stmt = (
        pg_insert(User)
        .values(clerk_user_id=clerk_user_id, email=email)
        .on_conflict_do_update(
            index_elements=[User.clerk_user_id],
            set_={"last_seen_at": func.now()},
        )
        .returning(User)
    )
    result = await session.execute(stmt)
    await session.commit()
    return result.scalar_one()


async def get_settings(session: AsyncSession, user_id: uuid.UUID) -> dict[str, Any]:
    row = await session.get(UserSettings, user_id)
    return dict(row.settings) if row else {}


async def put_settings(
    session: AsyncSession, user_id: uuid.UUID, settings_payload: dict[str, Any]
) -> dict[str, Any]:
    stmt = (
        pg_insert(UserSettings)
        .values(user_id=user_id, settings=settings_payload)
        .on_conflict_do_update(
            index_elements=[UserSettings.user_id],
            set_={"settings": settings_payload, "updated_at": func.now()},
        )
        .returning(UserSettings)
    )
    result = await session.execute(stmt)
    await session.commit()
    return dict(result.scalar_one().settings)
