"""Add submission packet workflow tables.

Revision ID: 20260426_0004
Revises: 20260426_0003
Create Date: 2026-04-26 00:30:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260426_0004"
down_revision = "20260426_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "submission_packets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("load_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("packet_reference", sa.String(length=100), nullable=False),
        sa.Column("destination_type", sa.String(length=40), nullable=False, server_default="other"),
        sa.Column("destination_name", sa.String(length=255), nullable=True),
        sa.Column("destination_email", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="draft"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_staff_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sent_by_staff_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["load_id"], ["loads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_staff_user_id"], ["staff_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sent_by_staff_user_id"], ["staff_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_submission_packets_organization_id", "submission_packets", ["organization_id"])
    op.create_index("ix_submission_packets_load_id", "submission_packets", ["load_id"])
    op.create_index("ix_submission_packets_status", "submission_packets", ["status"])
    op.create_index("ix_submission_packets_sent_at", "submission_packets", ["sent_at"])

    op.create_table(
        "submission_packet_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("submission_packet_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_type", sa.String(length=100), nullable=False),
        sa.Column("filename_snapshot", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["submission_packet_id"], ["submission_packets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["load_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_submission_packet_documents_submission_packet_id",
        "submission_packet_documents",
        ["submission_packet_id"],
    )
    op.create_index("ix_submission_packet_documents_document_id", "submission_packet_documents", ["document_id"])

    op.create_table(
        "submission_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("load_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("submission_packet_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_by_staff_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["load_id"], ["loads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["submission_packet_id"], ["submission_packets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_staff_user_id"], ["staff_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_submission_events_organization_id", "submission_events", ["organization_id"])
    op.create_index("ix_submission_events_load_id", "submission_events", ["load_id"])
    op.create_index("ix_submission_events_submission_packet_id", "submission_events", ["submission_packet_id"])


def downgrade() -> None:
    op.drop_index("ix_submission_events_submission_packet_id", table_name="submission_events")
    op.drop_index("ix_submission_events_load_id", table_name="submission_events")
    op.drop_index("ix_submission_events_organization_id", table_name="submission_events")
    op.drop_table("submission_events")

    op.drop_index("ix_submission_packet_documents_document_id", table_name="submission_packet_documents")
    op.drop_index("ix_submission_packet_documents_submission_packet_id", table_name="submission_packet_documents")
    op.drop_table("submission_packet_documents")

    op.drop_index("ix_submission_packets_sent_at", table_name="submission_packets")
    op.drop_index("ix_submission_packets_status", table_name="submission_packets")
    op.drop_index("ix_submission_packets_load_id", table_name="submission_packets")
    op.drop_index("ix_submission_packets_organization_id", table_name="submission_packets")
    op.drop_table("submission_packets")
