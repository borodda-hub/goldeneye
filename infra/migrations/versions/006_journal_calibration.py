"""Journal calibration columns — Phase 13

Adds the three columns required for Decision Quality:
- resolved_direction TEXT NULL  → analyst's manual hit/miss/neutral/unresolved
- thesis_id_at_write UUID NULL  → FK snapshot of the active thesis at create
- thesis_conviction_at_write INT NULL → conviction at create time, immutable

Existing rows get NULL for all three columns, so legacy entries still appear
in calibration via fallback to the user-entered confidence_pct field.

Revision ID: 006
Revises: 005
Create Date: 2026-05-12
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_decision_journals",
        sa.Column("resolved_direction", sa.Text, nullable=True),
    )
    op.add_column(
        "user_decision_journals",
        sa.Column(
            "thesis_id_at_write",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("theses.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "user_decision_journals",
        sa.Column("thesis_conviction_at_write", sa.Integer, nullable=True),
    )

    # CHECK constraints — added separately so the upgrade is idempotent in
    # the event we ever need to split + retry.
    op.create_check_constraint(
        "ck_journal_resolved_direction",
        "user_decision_journals",
        "resolved_direction IS NULL OR "
        "resolved_direction IN ('hit', 'miss', 'neutral', 'unresolved')",
    )
    op.create_check_constraint(
        "ck_journal_thesis_conviction_at_write",
        "user_decision_journals",
        "thesis_conviction_at_write IS NULL OR "
        "thesis_conviction_at_write BETWEEN 0 AND 100",
    )

    # Index supports the calibration query: group by conviction bucket
    # filtered to resolved entries only.
    op.create_index(
        "journal_calibration_idx",
        "user_decision_journals",
        ["thesis_conviction_at_write", "resolved_direction"],
        postgresql_where=sa.text("resolved_direction IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("journal_calibration_idx", table_name="user_decision_journals")
    op.drop_constraint(
        "ck_journal_thesis_conviction_at_write",
        "user_decision_journals",
        type_="check",
    )
    op.drop_constraint(
        "ck_journal_resolved_direction",
        "user_decision_journals",
        type_="check",
    )
    op.drop_column("user_decision_journals", "thesis_conviction_at_write")
    op.drop_column("user_decision_journals", "thesis_id_at_write")
    op.drop_column("user_decision_journals", "resolved_direction")
