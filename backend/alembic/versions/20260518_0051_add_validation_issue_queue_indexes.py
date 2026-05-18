"""add validation issue queue indexes

Revision ID: 20260518_0051
Revises: 20260516_0050
Create Date: 2026-05-18 00:00:00.000000
"""

from __future__ import annotations

from alembic import op

revision = "20260518_0051"
down_revision = "20260516_0050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_validation_issues_status_severity",
        "validation_issues",
        ["is_resolved", "severity"],
        unique=False,
    )
    op.create_index(
        "ix_validation_issues_org_status_load",
        "validation_issues",
        ["organization_id", "is_resolved", "load_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_validation_issues_org_status_load",
        table_name="validation_issues",
    )
    op.drop_index(
        "ix_validation_issues_status_severity",
        table_name="validation_issues",
    )
