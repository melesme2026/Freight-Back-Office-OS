"""add auth login indexes

Revision ID: 20260516_0050
Revises: 20260516_0049
Create Date: 2026-05-16 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260516_0050"
down_revision = "20260516_0049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_staff_users_email_active_role",
        "staff_users",
        ["email", "is_active", "role"],
        unique=False,
    )
    op.create_index(
        "ix_staff_users_org_lower_email",
        "staff_users",
        ["organization_id", sa.text("lower(email)")],
        unique=False,
    )
    op.create_index(
        "ix_staff_users_lower_email_org",
        "staff_users",
        [sa.text("lower(email)"), "organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_drivers_org_email_active",
        "drivers",
        ["organization_id", "email", "is_active"],
        unique=False,
    )
    op.create_index(
        "ix_drivers_org_lower_email",
        "drivers",
        ["organization_id", sa.text("lower(email)")],
        unique=False,
    )
    op.create_index(
        "ix_drivers_lower_email_org",
        "drivers",
        [sa.text("lower(email)"), "organization_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_drivers_lower_email_org", table_name="drivers")
    op.drop_index("ix_drivers_org_lower_email", table_name="drivers")
    op.drop_index("ix_drivers_org_email_active", table_name="drivers")
    op.drop_index("ix_staff_users_lower_email_org", table_name="staff_users")
    op.drop_index("ix_staff_users_org_lower_email", table_name="staff_users")
    op.drop_index("ix_staff_users_email_active_role", table_name="staff_users")
