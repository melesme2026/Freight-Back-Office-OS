"""Add accounting export mappings and integration settings.

Revision ID: 20260508_0038
Revises: 20260508_0036
Create Date: 2026-05-08 03:38:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260508_0038"
down_revision = "20260508_0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "accounting_export_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("accounting_category", sa.String(length=120), nullable=False, server_default="Freight Operations"),
        sa.Column("revenue_category", sa.String(length=120), nullable=False, server_default="Freight Revenue"),
        sa.Column("factoring_category", sa.String(length=120), nullable=False, server_default="Factoring"),
        sa.Column("settlement_category", sa.String(length=120), nullable=False, server_default="Settlements"),
        sa.Column("payment_category", sa.String(length=120), nullable=False, server_default="Customer Payments"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", name="uq_accounting_export_mappings_org"),
    )
    op.create_index("ix_accounting_export_mappings_organization_id", "accounting_export_mappings", ["organization_id"])

    op.create_table(
        "accounting_integration_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False, server_default="quickbooks"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("realm_id", sa.String(length=120), nullable=True),
        sa.Column("default_export_format", sa.String(length=20), nullable=False, server_default="csv"),
        sa.Column("sync_mode", sa.String(length=40), nullable=False, server_default="export_ready"),
        sa.Column("last_export_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", name="uq_accounting_integration_settings_org"),
    )
    op.create_index("ix_accounting_integration_settings_organization_id", "accounting_integration_settings", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_accounting_integration_settings_organization_id", table_name="accounting_integration_settings")
    op.drop_table("accounting_integration_settings")
    op.drop_index("ix_accounting_export_mappings_organization_id", table_name="accounting_export_mappings")
    op.drop_table("accounting_export_mappings")
