"""add demo_requests table

Revision ID: 20260505_0008
Revises: 20260427_0007
Create Date: 2026-05-05 00:08:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260505_0008"
down_revision = "20260427_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "demo_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=False),
        sa.Column("message", sa.String(length=5000), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="received"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_demo_requests_email", "demo_requests", ["email"])
    op.create_index("ix_demo_requests_status", "demo_requests", ["status"])
    op.create_index("ix_demo_requests_created_at", "demo_requests", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_demo_requests_created_at", table_name="demo_requests")
    op.drop_index("ix_demo_requests_status", table_name="demo_requests")
    op.drop_index("ix_demo_requests_email", table_name="demo_requests")
    op.drop_table("demo_requests")
