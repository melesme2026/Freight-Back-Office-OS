"""add hot path document indexes

Revision ID: 20260516_0049
Revises: 20260509_0048
Create Date: 2026-05-16 00:00:00.000000
"""

from __future__ import annotations

from alembic import op

revision = "20260516_0049"
down_revision = "20260509_0048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_load_documents_org_load_type_received",
        "load_documents",
        ["organization_id", "load_id", "document_type", "received_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_load_documents_org_load_type_received", table_name="load_documents")
