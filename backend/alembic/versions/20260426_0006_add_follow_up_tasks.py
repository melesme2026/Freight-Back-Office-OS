"""Add follow-up automation task table.

Revision ID: 20260426_0006
Revises: 20260426_0005
Create Date: 2026-04-26 03:15:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260426_0006"
down_revision = "20260426_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "follow_up_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("load_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("submission_packet_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payment_record_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("task_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="normal"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("recommended_action", sa.Text(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("snoozed_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_to_staff_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_system", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["load_id"], ["loads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["submission_packet_id"], ["submission_packets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["payment_record_id"], ["load_payment_records.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_to_staff_user_id"], ["staff_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_follow_up_tasks_organization_id", "follow_up_tasks", ["organization_id"])
    op.create_index("ix_follow_up_tasks_load_id", "follow_up_tasks", ["load_id"])
    op.create_index("ix_follow_up_tasks_submission_packet_id", "follow_up_tasks", ["submission_packet_id"])
    op.create_index("ix_follow_up_tasks_payment_record_id", "follow_up_tasks", ["payment_record_id"])
    op.create_index("ix_follow_up_tasks_status", "follow_up_tasks", ["status"])
    op.create_index("ix_follow_up_tasks_priority", "follow_up_tasks", ["priority"])
    op.create_index("ix_follow_up_tasks_due_at", "follow_up_tasks", ["due_at"])
    op.create_index("ix_follow_up_tasks_task_type", "follow_up_tasks", ["task_type"])


def downgrade() -> None:
    op.drop_index("ix_follow_up_tasks_task_type", table_name="follow_up_tasks")
    op.drop_index("ix_follow_up_tasks_due_at", table_name="follow_up_tasks")
    op.drop_index("ix_follow_up_tasks_priority", table_name="follow_up_tasks")
    op.drop_index("ix_follow_up_tasks_status", table_name="follow_up_tasks")
    op.drop_index("ix_follow_up_tasks_payment_record_id", table_name="follow_up_tasks")
    op.drop_index("ix_follow_up_tasks_submission_packet_id", table_name="follow_up_tasks")
    op.drop_index("ix_follow_up_tasks_load_id", table_name="follow_up_tasks")
    op.drop_index("ix_follow_up_tasks_organization_id", table_name="follow_up_tasks")
    op.drop_table("follow_up_tasks")
