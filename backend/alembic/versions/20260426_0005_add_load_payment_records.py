"""Add load payment reconciliation records.

Revision ID: 20260426_0005
Revises: 20260426_0004
Create Date: 2026-04-26 02:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260426_0005"
down_revision = "20260426_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "load_payment_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("load_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gross_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("expected_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("amount_received", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("payment_status", sa.String(length=32), nullable=False, server_default="not_submitted"),
        sa.Column("paid_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("factoring_used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("factor_name", sa.String(length=255), nullable=True),
        sa.Column("advance_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("advance_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("factoring_fee_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("reserve_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("reserve_paid_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("reserve_paid_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deduction_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("short_paid_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("dispute_reason", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_staff_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_staff_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["load_id"], ["loads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_staff_user_id"], ["staff_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_staff_user_id"], ["staff_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("load_id", name="uq_load_payment_records_load_id"),
    )

    op.create_index("ix_load_payment_records_organization_id", "load_payment_records", ["organization_id"])
    op.create_index("ix_load_payment_records_load_id", "load_payment_records", ["load_id"])
    op.create_index("ix_load_payment_records_payment_status", "load_payment_records", ["payment_status"])
    op.create_index("ix_load_payment_records_paid_date", "load_payment_records", ["paid_date"])


def downgrade() -> None:
    op.drop_index("ix_load_payment_records_paid_date", table_name="load_payment_records")
    op.drop_index("ix_load_payment_records_payment_status", table_name="load_payment_records")
    op.drop_index("ix_load_payment_records_load_id", table_name="load_payment_records")
    op.drop_index("ix_load_payment_records_organization_id", table_name="load_payment_records")
    op.drop_table("load_payment_records")
