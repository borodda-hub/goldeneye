"""Structured ex-ante decision capture — Phase 2 (Calibration Platform)

Adds the machine-resolvable claim to each decision so it can be auto-resolved
(Phase 3) instead of relying on a manual hit/miss mark:
- predicted_direction TEXT NULL → bullish / bearish / neutral
- horizon_days        INT  NULL → days until the claim resolves
- threshold_pct       NUMERIC NULL → move magnitude (in %) that counts as a hit;
                                     |move| below it resolves neutral/indeterminate
- anchor_price        NUMERIC NULL → instrument price at decision time; the move
                                     is measured from here

All nullable so existing entries (and prose-only decisions) are unaffected.

Revision ID: 007_decision_capture
Revises: 006
Create Date: 2026-06-06

NOTE: a sibling branch (accounts/Clerk) also revises 006 with revision id "007";
when that branch lands this becomes a second head off 006 and needs a one-line
`alembic merge`. They touch different tables, so the merge is mechanical.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_decision_capture"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_decision_journals",
        sa.Column("predicted_direction", sa.Text, nullable=True),
    )
    op.add_column(
        "user_decision_journals",
        sa.Column("horizon_days", sa.Integer, nullable=True),
    )
    op.add_column(
        "user_decision_journals",
        sa.Column("threshold_pct", sa.Numeric, nullable=True),
    )
    op.add_column(
        "user_decision_journals",
        sa.Column("anchor_price", sa.Numeric, nullable=True),
    )
    op.create_check_constraint(
        "ck_journal_predicted_direction",
        "user_decision_journals",
        "predicted_direction IS NULL OR "
        "predicted_direction IN ('bullish', 'bearish', 'neutral')",
    )
    op.create_check_constraint(
        "ck_journal_horizon_days",
        "user_decision_journals",
        "horizon_days IS NULL OR horizon_days > 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_journal_horizon_days", "user_decision_journals", type_="check"
    )
    op.drop_constraint(
        "ck_journal_predicted_direction", "user_decision_journals", type_="check"
    )
    op.drop_column("user_decision_journals", "anchor_price")
    op.drop_column("user_decision_journals", "threshold_pct")
    op.drop_column("user_decision_journals", "horizon_days")
    op.drop_column("user_decision_journals", "predicted_direction")
