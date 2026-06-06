"""merge the two migration heads into one

Two feature lines both branched off 006:
- accounts/Clerk           → 007 (users + user_settings)
- decision-capture (P2)    → 007_decision_capture → 008_auto_resolution (P3)

They touch disjoint tables (users/user_settings vs. user_decision_journals), so
this is a pure no-op merge that re-joins the history into a single head.

Revision ID: 009_merge_heads
Revises: 007, 008_auto_resolution
Create Date: 2026-06-06
"""
from typing import Sequence, Union

revision: str = "009_merge_heads"
down_revision: Union[str, Sequence[str], None] = ("007", "008_auto_resolution")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
