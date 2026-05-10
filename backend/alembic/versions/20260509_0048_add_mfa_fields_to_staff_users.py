"""add mfa foundation fields to staff users

Revision ID: 20260509_0048
Revises: 20260508_0041
Create Date: 2026-05-09 00:48:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "20260509_0048"
down_revision = "20260508_0041"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    if not _column_exists("staff_users", "mfa_enabled"):
        op.add_column(
            "staff_users",
            sa.Column(
                "mfa_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )

    if not _column_exists("staff_users", "mfa_totp_secret"):
        op.add_column(
            "staff_users",
            sa.Column("mfa_totp_secret", sa.Text(), nullable=True),
        )

    if not _column_exists("staff_users", "mfa_enabled_at"):
        op.add_column(
            "staff_users",
            sa.Column("mfa_enabled_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    if _column_exists("staff_users", "mfa_enabled_at"):
        op.drop_column("staff_users", "mfa_enabled_at")

    if _column_exists("staff_users", "mfa_totp_secret"):
        op.drop_column("staff_users", "mfa_totp_secret")

    if _column_exists("staff_users", "mfa_enabled"):
        op.drop_column("staff_users", "mfa_enabled")