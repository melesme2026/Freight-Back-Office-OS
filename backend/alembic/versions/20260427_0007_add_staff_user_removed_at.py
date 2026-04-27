"""add removed_at column to staff_users for soft removal

Revision ID: 20260427_0007
Revises: 20260426_0006
Create Date: 2026-04-27 00:00:07.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260427_0007"
down_revision = "20260426_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("staff_users", sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("staff_users", "removed_at")
