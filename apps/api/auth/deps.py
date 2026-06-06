"""FastAPI auth dependencies (Clerk).

`get_optional_user` resolves the signed-in user from a bearer token (or None for
anonymous). `get_current_user` requires sign-in **only when accounts are
configured** — when Clerk is off (open demo) it returns None so anonymous writes
keep working. Routers do `user.id if user else None`.
"""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.auth.clerk import clerk_configured, verify_token
from apps.api.db.session import get_db
from apps.api.models.orm.users import User
from apps.api.repos import users as users_repo


async def get_optional_user(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_db),
) -> User | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    claims = verify_token(parts[1].strip())
    sub = claims.get("sub") if claims else None
    if not sub:
        return None
    return await users_repo.upsert(session, clerk_user_id=sub)


async def get_current_user(
    user: User | None = Depends(get_optional_user),
) -> User | None:
    if not clerk_configured():
        return None
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to save your work")
    return user
