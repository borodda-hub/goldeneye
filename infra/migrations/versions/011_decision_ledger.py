"""Phase B4 — immutable decision/audit ledger.

Adds `decision_ledger_events`: an append-only, tamper-evident record of every
decision's lifecycle (`created` / `resolved` / `amended`). It SHADOWS the
mutable `user_decision_journals` row — the journal stays live mutable state;
this table is its immutable audit trail.

Immutability is **DB-enforced, not convention**:
- A `BEFORE UPDATE OR DELETE` trigger RAISES — the database itself rejects any
  mutation/delete attempt, so a buggy or compromised service cannot rewrite
  history. INSERT is the only permitted operation.
- The `source` column has a CHECK that permits only `'live'` — there is no
  `backfill` value, so fabricated/reconstructed history is structurally
  impossible to record (an audit ledger cannot be honestly backfilled).
- Tamper-EVIDENCE is layered on top in the app: each row's `row_hash` chains off
  the previous event for the same decision, so an out-of-band edit that bypasses
  the trigger (e.g. a superuser direct-SQL) is still detectable via chain verify.

Revision ID: 011_decision_ledger
Revises: 010_theses_user_scope
Create Date: 2026-06-10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "011_decision_ledger"
down_revision: Union[str, None] = "010_theses_user_scope"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_IMMUTABLE_FN = """
CREATE OR REPLACE FUNCTION decision_ledger_events_immutable()
RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION
        'decision_ledger_events is append-only: % is not permitted', TG_OP
        USING ERRCODE = 'restrict_violation';
END;
$$ LANGUAGE plpgsql;
"""

_IMMUTABLE_TRIGGER = """
CREATE TRIGGER decision_ledger_events_no_mutate
BEFORE UPDATE OR DELETE ON decision_ledger_events
FOR EACH ROW EXECUTE FUNCTION decision_ledger_events_immutable();
"""


def upgrade() -> None:
    op.create_table(
        "decision_ledger_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        # Global monotonic append order. Identity(always) → the value cannot be
        # supplied on INSERT, so append order is owned by the database.
        sa.Column(
            "seq",
            sa.BigInteger,
            sa.Identity(always=True),
            nullable=False,
            unique=True,
        ),
        sa.Column("decision_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Copied from the decision at append time so the ledger read scopes by it
        # exactly like the journal (B3). NULL = the anonymous/demo pool.
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.Text, nullable=False),
        # Domain time of the event (decision created_at / resolved_at / amend time).
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        # Wall-clock append time.
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "source", sa.Text, nullable=False, server_default=sa.text("'live'")
        ),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("prev_hash", sa.Text, nullable=True),
        sa.Column("row_hash", sa.Text, nullable=False),
        sa.ForeignKeyConstraint(
            ["decision_id"],
            ["user_decision_journals.id"],
            name="fk_ledger_decision_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_ledger_user_id", ondelete="RESTRICT"
        ),
        sa.CheckConstraint(
            "event_type IN ('created', 'resolved', 'amended')",
            name="ck_ledger_event_type",
        ),
        # The honesty guard: only live-captured events exist. No 'backfill'.
        sa.CheckConstraint("source = 'live'", name="ck_ledger_source_live"),
    )
    op.create_index(
        "ix_ledger_user_decision_seq",
        "decision_ledger_events",
        ["user_id", "decision_id", "seq"],
    )
    op.create_index(
        "ix_ledger_decision_seq",
        "decision_ledger_events",
        ["decision_id", "seq"],
    )

    # DB-enforced immutability (the enforcement, not convention).
    op.execute(_IMMUTABLE_FN)
    op.execute(_IMMUTABLE_TRIGGER)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS decision_ledger_events_no_mutate "
        "ON decision_ledger_events"
    )
    op.execute("DROP FUNCTION IF EXISTS decision_ledger_events_immutable()")
    op.drop_index("ix_ledger_decision_seq", table_name="decision_ledger_events")
    op.drop_index(
        "ix_ledger_user_decision_seq", table_name="decision_ledger_events"
    )
    op.drop_table("decision_ledger_events")
