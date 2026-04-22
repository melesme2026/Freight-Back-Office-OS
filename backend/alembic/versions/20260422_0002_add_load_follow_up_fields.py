"""Add load follow-up owner and next touch fields.

Revision ID: 20260422_0002
Revises: 20260414_0001
Create Date: 2026-04-22 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


revision = "20260422_0002"
down_revision = "20260414_0001"
branch_labels = None
depends_on = None

FK_NAME = "fk_loads_follow_up_owner_id_staff_users"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    existing_columns = {col["name"] for col in inspector.get_columns("loads")}

    if "next_follow_up_at" not in existing_columns:
        op.add_column(
            "loads",
            sa.Column("next_follow_up_at", sa.DateTime(timezone=True), nullable=True),
        )

    if "follow_up_owner_id" not in existing_columns:
        op.add_column(
            "loads",
            sa.Column("follow_up_owner_id", postgresql.UUID(as_uuid=True), nullable=True),
        )

    existing_fks = {fk["name"] for fk in inspector.get_foreign_keys("loads") if fk.get("name")}

    if FK_NAME not in existing_fks:
        op.create_foreign_key(
            FK_NAME,
            "loads",
            "staff_users",
            ["follow_up_owner_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    existing_fks = {fk["name"] for fk in inspector.get_foreign_keys("loads") if fk.get("name")}
    if FK_NAME in existing_fks:
        op.drop_constraint(FK_NAME, "loads", type_="foreignkey")

    existing_columns = {col["name"] for col in inspector.get_columns("loads")}

    if "follow_up_owner_id" in existing_columns:
        op.drop_column("loads", "follow_up_owner_id")

    if "next_follow_up_at" in existing_columns:
        op.drop_column("loads", "next_follow_up_at")