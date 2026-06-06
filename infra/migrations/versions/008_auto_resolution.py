"""Auto-resolution provenance — Phase 3 (Calibration Platform)

The engine resolves open structured decisions from real market data and writes
the result into the existing `resolved_direction` column (so calibration picks it
up unchanged). These two columns record provenance:
- resolved_at    TIMESTAMPTZ NULL → when the resolution was set
- auto_resolved  BOOLEAN NOT NULL DEFAULT false → machine-resolved vs. manual

Auto-resolution only ever fills entries whose resolved_direction is still NULL,
so a manual mark is never overwritten.

Revision ID: 008_auto_resolution
Revises: 007_decision_capture
Create Date: 2026-06-06
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008_auto_resolution"
down_revision: Union[str, None] = "007_decision_capture"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_decision_journals",
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "user_decision_journals",
        sa.Column(
            "auto_resolved",
            sa.Boolean,
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("user_decision_journals", "auto_resolved")
    op.drop_column("user_decision_journals", "resolved_at")
