"""Add load follow-up owner and next touch fields.

Revision ID: 20260422_0002
Revises: 20260414_0001
Create Date: 2026-04-22 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260422_0002"
down_revision = "20260414_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("loads", sa.Column("next_follow_up_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("loads", sa.Column("follow_up_owner_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_loads_follow_up_owner_id_staff_users",
        "loads",
        "staff_users",
        ["follow_up_owner_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_loads_follow_up_owner_id_staff_users", "loads", type_="foreignkey")
    op.drop_column("loads", "follow_up_owner_id")
    op.drop_column("loads", "next_follow_up_at")
