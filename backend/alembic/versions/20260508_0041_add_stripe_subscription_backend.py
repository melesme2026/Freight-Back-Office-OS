"""Add Stripe subscription backend organization fields.

Revision ID: 20260508_0041
Revises: 20260508_0038
Create Date: 2026-05-08 00:41:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


revision = "20260508_0041"
down_revision = "20260508_0038"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _index_exists(table_name: str, index_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return index_name in {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    if not _column_exists("organizations", "plan_key"):
        op.add_column(
            "organizations",
            sa.Column("plan_key", sa.String(length=30), server_default="none", nullable=False),
        )

    if not _column_exists("organizations", "subscription_status"):
        op.add_column(
            "organizations",
            sa.Column(
                "subscription_status",
                sa.String(length=30),
                server_default="none",
                nullable=False,
            ),
        )

    if not _column_exists("organizations", "trial_start"):
        op.add_column(
            "organizations",
            sa.Column("trial_start", sa.DateTime(timezone=True), nullable=True),
        )

    if not _column_exists("organizations", "trial_end"):
        op.add_column(
            "organizations",
            sa.Column("trial_end", sa.DateTime(timezone=True), nullable=True),
        )

    if not _column_exists("organizations", "current_period_start"):
        op.add_column(
            "organizations",
            sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        )

    if not _column_exists("organizations", "current_period_end"):
        op.add_column(
            "organizations",
            sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        )

    if not _column_exists("organizations", "cancel_at_period_end"):
        op.add_column(
            "organizations",
            sa.Column(
                "cancel_at_period_end",
                sa.Boolean(),
                server_default="false",
                nullable=False,
            ),
        )

    if not _column_exists("organizations", "last_payment_status"):
        op.add_column(
            "organizations",
            sa.Column("last_payment_status", sa.String(length=30), nullable=True),
        )

    if not _table_exists("stripe_webhook_events"):
        op.create_table(
            "stripe_webhook_events",
            sa.Column("stripe_event_id", sa.String(length=255), nullable=False),
            sa.Column("event_type", sa.String(length=100), nullable=False),
            sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("status", sa.String(length=30), server_default="processed", nullable=False),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("stripe_event_id"),
        )

    if not _index_exists("stripe_webhook_events", "ix_stripe_webhook_events_event_type"):
        op.create_index(
            "ix_stripe_webhook_events_event_type",
            "stripe_webhook_events",
            ["event_type"],
            unique=False,
        )

    if not _index_exists("stripe_webhook_events", "ix_stripe_webhook_events_stripe_event_id"):
        op.create_index(
            "ix_stripe_webhook_events_stripe_event_id",
            "stripe_webhook_events",
            ["stripe_event_id"],
            unique=True,
        )


def downgrade() -> None:
    if _table_exists("stripe_webhook_events"):
        if _index_exists("stripe_webhook_events", "ix_stripe_webhook_events_stripe_event_id"):
            op.drop_index(
                "ix_stripe_webhook_events_stripe_event_id",
                table_name="stripe_webhook_events",
            )

        if _index_exists("stripe_webhook_events", "ix_stripe_webhook_events_event_type"):
            op.drop_index(
                "ix_stripe_webhook_events_event_type",
                table_name="stripe_webhook_events",
            )

        op.drop_table("stripe_webhook_events")

    if _column_exists("organizations", "last_payment_status"):
        op.drop_column("organizations", "last_payment_status")

    if _column_exists("organizations", "cancel_at_period_end"):
        op.drop_column("organizations", "cancel_at_period_end")

    if _column_exists("organizations", "current_period_end"):
        op.drop_column("organizations", "current_period_end")

    if _column_exists("organizations", "current_period_start"):
        op.drop_column("organizations", "current_period_start")

    if _column_exists("organizations", "trial_end"):
        op.drop_column("organizations", "trial_end")

    if _column_exists("organizations", "trial_start"):
        op.drop_column("organizations", "trial_start")

    if _column_exists("organizations", "subscription_status"):
        op.drop_column("organizations", "subscription_status")

    if _column_exists("organizations", "plan_key"):
        op.drop_column("organizations", "plan_key")