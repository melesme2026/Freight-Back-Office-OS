"""operationalize demo requests

Revision ID: 20260507_0010
Revises: 20260507_0009
Create Date: 2026-05-07 01:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260507_0010"
down_revision = "20260507_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("demo_requests", sa.Column("phone", sa.String(length=50), nullable=True))
    op.add_column("demo_requests", sa.Column("fleet_size", sa.String(length=100), nullable=True))
    op.add_column("demo_requests", sa.Column("source_ip", sa.String(length=64), nullable=True))
    op.add_column("demo_requests", sa.Column("user_agent", sa.String(length=512), nullable=True))
    op.execute("UPDATE demo_requests SET status = 'new' WHERE status = 'received'")
    op.alter_column(
        "demo_requests",
        "status",
        existing_type=sa.String(length=32),
        server_default="new",
        existing_nullable=False,
    )


def downgrade() -> None:
    op.execute("UPDATE demo_requests SET status = 'received' WHERE status = 'new'")
    op.alter_column(
        "demo_requests",
        "status",
        existing_type=sa.String(length=50),
        server_default="received",
        existing_nullable=False,
    )
    op.drop_column("demo_requests", "user_agent")
    op.drop_column("demo_requests", "source_ip")
    op.drop_column("demo_requests", "fleet_size")
    op.drop_column("demo_requests", "phone")
