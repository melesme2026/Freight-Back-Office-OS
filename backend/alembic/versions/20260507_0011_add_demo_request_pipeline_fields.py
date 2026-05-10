"""add demo request lead pipeline fields

Revision ID: 20260507_0011
Revises: 20260507_0010
Create Date: 2026-05-07 02:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "20260507_0011"
down_revision = "20260507_0010"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _index_exists(table_name: str, index_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return index_name in {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    if not _column_exists("demo_requests", "notes"):
        op.add_column("demo_requests", sa.Column("notes", sa.Text(), nullable=True))

    if not _column_exists("demo_requests", "next_follow_up_at"):
        op.add_column(
            "demo_requests",
            sa.Column("next_follow_up_at", sa.DateTime(timezone=True), nullable=True),
        )

    if not _index_exists("demo_requests", "ix_demo_requests_next_follow_up_at"):
        op.create_index(
            "ix_demo_requests_next_follow_up_at",
            "demo_requests",
            ["next_follow_up_at"],
        )

    op.execute("UPDATE demo_requests SET status = 'lost' WHERE status = 'closed'")


def downgrade() -> None:
    op.execute("UPDATE demo_requests SET status = 'closed' WHERE status = 'lost'")

    if _index_exists("demo_requests", "ix_demo_requests_next_follow_up_at"):
        op.drop_index("ix_demo_requests_next_follow_up_at", table_name="demo_requests")

    if _column_exists("demo_requests", "next_follow_up_at"):
        op.drop_column("demo_requests", "next_follow_up_at")

    if _column_exists("demo_requests", "notes"):
        op.drop_column("demo_requests", "notes")