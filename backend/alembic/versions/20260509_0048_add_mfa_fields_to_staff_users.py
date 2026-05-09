"""add mfa foundation fields to staff users

Revision ID: 20260509_0048
Revises: 20260508_0041
Create Date: 2026-05-09 00:48:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260509_0048"
down_revision = "20260508_0041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("staff_users", sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("staff_users", sa.Column("mfa_totp_secret", sa.Text(), nullable=True))
    op.add_column("staff_users", sa.Column("mfa_enabled_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("staff_users", "mfa_enabled_at")
    op.drop_column("staff_users", "mfa_totp_secret")
    op.drop_column("staff_users", "mfa_enabled")
