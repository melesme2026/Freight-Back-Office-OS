"""expand notifications for operational email events

Revision ID: 20260507_0009
Revises: 20260505_0008
Create Date: 2026-05-07 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260507_0009"
down_revision = "20260505_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("notifications", "organization_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)
    op.add_column("notifications", sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("notifications", sa.Column("broker_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("notifications", sa.Column("demo_request_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("notifications", sa.Column("recipient", sa.String(length=255), nullable=True))
    op.create_foreign_key("fk_notifications_document_id_load_documents", "notifications", "load_documents", ["document_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_notifications_broker_id_brokers", "notifications", "brokers", ["broker_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_notifications_demo_request_id_demo_requests", "notifications", "demo_requests", ["demo_request_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_notifications_document_id", "notifications", ["document_id"])
    op.create_index("ix_notifications_broker_id", "notifications", ["broker_id"])
    op.create_index("ix_notifications_demo_request_id", "notifications", ["demo_request_id"])


def downgrade() -> None:
    op.drop_index("ix_notifications_demo_request_id", table_name="notifications")
    op.drop_index("ix_notifications_broker_id", table_name="notifications")
    op.drop_index("ix_notifications_document_id", table_name="notifications")
    op.drop_constraint("fk_notifications_demo_request_id_demo_requests", "notifications", type_="foreignkey")
    op.drop_constraint("fk_notifications_broker_id_brokers", "notifications", type_="foreignkey")
    op.drop_constraint("fk_notifications_document_id_load_documents", "notifications", type_="foreignkey")
    op.drop_column("notifications", "recipient")
    op.drop_column("notifications", "demo_request_id")
    op.drop_column("notifications", "broker_id")
    op.drop_column("notifications", "document_id")
    op.alter_column("notifications", "organization_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)
