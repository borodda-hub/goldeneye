"""Accounts — users + user_settings (Clerk).

Optional account layer. `users` mirrors Clerk identities (one row per user,
upserted on first authenticated request); `user_settings` stores each user's UI
preferences (the `goldeneye:` localStorage payload) so they resume across
devices. Personal-artifact tables already carry a nullable `user_id` (migration
002); 008 scopes them + adds it to `theses`.

Revision ID: 007
Revises: 006
Create Date: 2026-06-06
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("clerk_user_id", sa.Text, nullable=False),
        sa.Column("email", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_users_clerk_user_id", "users", ["clerk_user_id"], unique=True
    )
    op.create_table(
        "user_settings",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "settings",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("user_settings")
    op.drop_index("ix_users_clerk_user_id", table_name="users")
    op.drop_table("users")
