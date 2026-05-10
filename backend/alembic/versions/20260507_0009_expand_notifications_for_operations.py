"""expand notifications for operational email events

Revision ID: 20260507_0009
Revises: 20260505_0008
Create Date: 2026-05-07 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


revision = "20260507_0009"
down_revision = "20260505_0008"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _index_exists(table_name: str, index_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return index_name in {index["name"] for index in inspector.get_indexes(table_name)}


def _foreign_key_exists(table_name: str, constraint_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return constraint_name in {
        fk.get("name")
        for fk in inspector.get_foreign_keys(table_name)
    }


def upgrade() -> None:
    op.alter_column(
        "notifications",
        "organization_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )

    if not _column_exists("notifications", "document_id"):
        op.add_column(
            "notifications",
            sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        )

    if not _column_exists("notifications", "broker_id"):
        op.add_column(
            "notifications",
            sa.Column("broker_id", postgresql.UUID(as_uuid=True), nullable=True),
        )

    if not _column_exists("notifications", "demo_request_id"):
        op.add_column(
            "notifications",
            sa.Column("demo_request_id", postgresql.UUID(as_uuid=True), nullable=True),
        )

    if not _column_exists("notifications", "recipient"):
        op.add_column(
            "notifications",
            sa.Column("recipient", sa.String(length=255), nullable=True),
        )

    if not _foreign_key_exists("notifications", "fk_notifications_document_id_load_documents"):
        op.create_foreign_key(
            "fk_notifications_document_id_load_documents",
            "notifications",
            "load_documents",
            ["document_id"],
            ["id"],
            ondelete="SET NULL",
        )

    if not _foreign_key_exists("notifications", "fk_notifications_broker_id_brokers"):
        op.create_foreign_key(
            "fk_notifications_broker_id_brokers",
            "notifications",
            "brokers",
            ["broker_id"],
            ["id"],
            ondelete="SET NULL",
        )

    if not _foreign_key_exists("notifications", "fk_notifications_demo_request_id_demo_requests"):
        op.create_foreign_key(
            "fk_notifications_demo_request_id_demo_requests",
            "notifications",
            "demo_requests",
            ["demo_request_id"],
            ["id"],
            ondelete="SET NULL",
        )

    if not _index_exists("notifications", "ix_notifications_document_id"):
        op.create_index("ix_notifications_document_id", "notifications", ["document_id"])

    if not _index_exists("notifications", "ix_notifications_broker_id"):
        op.create_index("ix_notifications_broker_id", "notifications", ["broker_id"])

    if not _index_exists("notifications", "ix_notifications_demo_request_id"):
        op.create_index("ix_notifications_demo_request_id", "notifications", ["demo_request_id"])


def downgrade() -> None:
    if _index_exists("notifications", "ix_notifications_demo_request_id"):
        op.drop_index("ix_notifications_demo_request_id", table_name="notifications")

    if _index_exists("notifications", "ix_notifications_broker_id"):
        op.drop_index("ix_notifications_broker_id", table_name="notifications")

    if _index_exists("notifications", "ix_notifications_document_id"):
        op.drop_index("ix_notifications_document_id", table_name="notifications")

    if _foreign_key_exists("notifications", "fk_notifications_demo_request_id_demo_requests"):
        op.drop_constraint(
            "fk_notifications_demo_request_id_demo_requests",
            "notifications",
            type_="foreignkey",
        )

    if _foreign_key_exists("notifications", "fk_notifications_broker_id_brokers"):
        op.drop_constraint(
            "fk_notifications_broker_id_brokers",
            "notifications",
            type_="foreignkey",
        )

    if _foreign_key_exists("notifications", "fk_notifications_document_id_load_documents"):
        op.drop_constraint(
            "fk_notifications_document_id_load_documents",
            "notifications",
            type_="foreignkey",
        )

    if _column_exists("notifications", "recipient"):
        op.drop_column("notifications", "recipient")

    if _column_exists("notifications", "demo_request_id"):
        op.drop_column("notifications", "demo_request_id")

    if _column_exists("notifications", "broker_id"):
        op.drop_column("notifications", "broker_id")

    if _column_exists("notifications", "document_id"):
        op.drop_column("notifications", "document_id")

    op.alter_column(
        "notifications",
        "organization_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )