"""Create baseline application schema from SQLAlchemy metadata.

Revision ID: 20260414_0001
Revises:
Create Date: 2026-04-14 00:00:00.000000
"""

from __future__ import annotations

from alembic import op

from app.core.database import Base
import app.domain.models  # noqa: F401


# revision identifiers, used by Alembic.
revision = "20260414_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, tables=_baseline_tables())


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind, tables=list(reversed(_baseline_tables())))


def _baseline_tables():
    """Return tables that existed in the 2026-04-14 baseline schema only."""

    baseline_table_names = [
        "api_clients",
        "audit_logs",
        "billing_invoice_lines",
        "billing_invoices",
        "brokers",
        "customer_accounts",
        "drivers",
        "extracted_fields",
        "ledger_entries",
        "load_documents",
        "loads",
        "notifications",
        "onboarding_checklists",
        "organizations",
        "payment_methods",
        "payments",
        "referrals",
        "service_plans",
        "staff_users",
        "subscriptions",
        "support_tickets",
        "usage_records",
        "validation_issues",
        "workflow_events",
    ]
    return [Base.metadata.tables[name] for name in baseline_table_names]
