"""add demo request lead pipeline fields

Revision ID: 20260507_0011
Revises: 20260507_0010
Create Date: 2026-05-07 02:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260507_0011"
down_revision = "20260507_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("demo_requests", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column(
        "demo_requests",
        sa.Column("next_follow_up_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_demo_requests_next_follow_up_at",
        "demo_requests",
        ["next_follow_up_at"],
    )
    op.execute("UPDATE demo_requests SET status = 'lost' WHERE status = 'closed'")


def downgrade() -> None:
    op.execute("UPDATE demo_requests SET status = 'closed' WHERE status = 'lost'")
    op.drop_index("ix_demo_requests_next_follow_up_at", table_name="demo_requests")
    op.drop_column("demo_requests", "next_follow_up_at")
    op.drop_column("demo_requests", "notes")
