"""Phase B3a — per-user scoping at the data layer (theses.user_id + scope indexes).

Adds the missing `user_id` to `theses` and the per-user indexes that the scoped
repos use. This is the *data-layer* half of B3 (R3): the schema gains the
capability to isolate per user; the routers/auth that *populate* and *enforce*
it land in B3b. Existing rows keep `user_id NULL` (the shared anonymous/demo
pool), so behavior is unchanged until B3b wires identity.

- `theses.user_id`  UUID NULL, FK → users(id) ON DELETE RESTRICT
    Nullable FK: real users get referential integrity; NULL preserves the
    anonymous pool. RESTRICT (not cascade/set-null) — thesis rows are
    decision-ledger data we must never silently delete or orphan.
- Active-thesis uniqueness swaps from global per-instrument to per-user:
    drop `one_active_thesis_per_instrument` (UNIQUE(instrument_code) WHERE active)
    → `one_active_thesis_per_user_instrument` (UNIQUE(user_id, instrument_code)
      WHERE active). Postgres treats NULL user_id as distinct, so the anonymous
    pool's single-active is enforced by the repo (`replace_active` scopes its
    deactivate to the requester scope, incl. the NULL branch), not the index.
- Scope read indexes: (user_id, created_at) on journals + scenario_runs,
    (user_id, active) on theses.

Revision ID: 010_theses_user_scope
Revises: 009_merge_heads
Create Date: 2026-06-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "010_theses_user_scope"
down_revision: Union[str, None] = "009_merge_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "theses",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_theses_user_id",
        "theses",
        "users",
        ["user_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # Active-thesis uniqueness → per (user_id, instrument_code).
    op.drop_index("one_active_thesis_per_instrument", table_name="theses")
    op.create_index(
        "one_active_thesis_per_user_instrument",
        "theses",
        ["user_id", "instrument_code"],
        unique=True,
        postgresql_where=sa.text("active"),
    )

    # Per-user read indexes.
    op.create_index(
        "ix_theses_user_active", "theses", ["user_id", "active"]
    )
    op.create_index(
        "ix_journal_user_created",
        "user_decision_journals",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_scenario_runs_user_created",
        "scenario_runs",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_scenario_runs_user_created", table_name="scenario_runs")
    op.drop_index("ix_journal_user_created", table_name="user_decision_journals")
    op.drop_index("ix_theses_user_active", table_name="theses")
    op.drop_index(
        "one_active_thesis_per_user_instrument", table_name="theses"
    )
    op.create_index(
        "one_active_thesis_per_instrument",
        "theses",
        ["instrument_code"],
        unique=True,
        postgresql_where=sa.text("active"),
    )
    op.drop_constraint("fk_theses_user_id", "theses", type_="foreignkey")
    op.drop_column("theses", "user_id")
