"""Add operational factoring workflow support.

Revision ID: 20260508_0036
Revises: 20260507_0011
Create Date: 2026-05-08 00:36:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260508_0036"
down_revision = "20260507_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "factoring_companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("default_reserve_percent", sa.Numeric(6, 3), nullable=False, server_default="0"),
        sa.Column("default_fee_percent", sa.Numeric(6, 3), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "company_name", name="uq_factoring_companies_org_name"),
    )
    op.create_index("ix_factoring_companies_organization_id", "factoring_companies", ["organization_id"])

    op.add_column("load_payment_records", sa.Column("factoring_company_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("load_payment_records", sa.Column("factoring_status", sa.String(length=32), nullable=False, server_default="not_factored"))
    op.add_column("load_payment_records", sa.Column("reconciliation_status", sa.String(length=32), nullable=False, server_default="unreconciled"))
    op.add_column("load_payment_records", sa.Column("factoring_fee_percent", sa.Numeric(6, 3), nullable=True))
    op.add_column("load_payment_records", sa.Column("factoring_notes", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_load_payment_records_factoring_company_id",
        "load_payment_records",
        "factoring_companies",
        ["factoring_company_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_load_payment_records_factoring_status", "load_payment_records", ["factoring_status"])
    op.create_index("ix_load_payment_records_reconciliation_status", "load_payment_records", ["reconciliation_status"])


def downgrade() -> None:
    op.drop_index("ix_load_payment_records_reconciliation_status", table_name="load_payment_records")
    op.drop_index("ix_load_payment_records_factoring_status", table_name="load_payment_records")
    op.drop_constraint("fk_load_payment_records_factoring_company_id", "load_payment_records", type_="foreignkey")
    op.drop_column("load_payment_records", "factoring_notes")
    op.drop_column("load_payment_records", "factoring_fee_percent")
    op.drop_column("load_payment_records", "reconciliation_status")
    op.drop_column("load_payment_records", "factoring_status")
    op.drop_column("load_payment_records", "factoring_company_id")
    op.drop_index("ix_factoring_companies_organization_id", table_name="factoring_companies")
    op.drop_table("factoring_companies")
