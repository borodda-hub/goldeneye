"""Current-user endpoints (`/v1/me`) — identity + per-user settings sync."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.auth.deps import get_current_user, get_optional_user
from apps.api.db.session import get_db
from apps.api.models.orm.users import User
from apps.api.repos import users as users_repo

router = APIRouter(prefix="/v1/me", tags=["me"])


@router.get("")
async def get_me(user: User | None = Depends(get_optional_user)) -> dict[str, Any]:
    """The signed-in user (or null when anonymous / accounts off)."""
    if user is None:
        return {"user": None}
    return {
        "user": {
            "id": str(user.id),
            "clerk_user_id": user.clerk_user_id,
            "email": user.email,
        }
    }


class SettingsBody(BaseModel):
    settings: dict[str, Any]


@router.get("/settings")
async def get_my_settings(
    user: User | None = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if user is None:  # accounts off
        return {"settings": {}}
    return {"settings": await users_repo.get_settings(session, user.id)}


@router.put("/settings")
async def put_my_settings(
    body: SettingsBody,
    user: User | None = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if user is None:  # accounts off
        return {"settings": {}}
    return {
        "settings": await users_repo.put_settings(session, user.id, body.settings)
    }
