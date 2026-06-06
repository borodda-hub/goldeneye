"""ORM models for accounts (Clerk) — users + per-user settings.

Accounts are optional: when Clerk isn't configured the API stays open and these
tables go unused. When it is, a row is upserted per Clerk user on their first
authenticated request, and personal artifacts (journal, paper, scenarios,
theses) + UI settings are scoped to `user_id`.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Stable Clerk identifier (the `sub` claim). Email lives in the Clerk
    # dashboard; mirrored here lazily/optionally.
    clerk_user_id: Mapped[str] = mapped_column(
        Text, nullable=False, unique=True, index=True
    )
    email: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    # Opaque UI preferences (theme, saved views, …) — the `goldeneye:` localStorage
    # payload, so a signed-in user resumes across devices.
    settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
