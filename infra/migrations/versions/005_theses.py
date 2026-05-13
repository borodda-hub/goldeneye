"""Theses table — Working Thesis card (Phase 12)

Revision ID: 005
Revises: 004
Create Date: 2026-05-12
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "theses",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("instrument_code", sa.Text, nullable=False, server_default="NG"),
        sa.Column("statement", sa.Text, nullable=False),
        sa.Column(
            "supporting_evidence",
            postgresql.JSONB,
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "contradicting_evidence",
            postgresql.JSONB,
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "missing_data",
            postgresql.JSONB,
            nullable=False,
            server_default="[]",
        ),
        sa.Column("conviction_pct", sa.Integer, nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "active",
            sa.Boolean,
            nullable=False,
            server_default="true",
        ),
        sa.CheckConstraint(
            "conviction_pct BETWEEN 0 AND 100", name="ck_theses_conviction_pct"
        ),
        sa.CheckConstraint(
            "char_length(statement) > 0", name="ck_theses_statement_nonempty"
        ),
    )
    # Only one active thesis per instrument.
    op.create_index(
        "one_active_thesis_per_instrument",
        "theses",
        ["instrument_code"],
        unique=True,
        postgresql_where=sa.text("active"),
    )
    # Calibration queries scan historical theses by instrument + time.
    op.create_index(
        "theses_instrument_time_idx",
        "theses",
        ["instrument_code", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("theses_instrument_time_idx", table_name="theses")
    op.drop_index("one_active_thesis_per_instrument", table_name="theses")
    op.drop_table("theses")
