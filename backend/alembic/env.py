from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.core.database import Base

from app.domain.models.api_client import ApiClient
from app.domain.models.audit_log import AuditLog
from app.domain.models.billing_invoice import BillingInvoice
from app.domain.models.billing_invoice_line import BillingInvoiceLine
from app.domain.models.broker import Broker
from app.domain.models.customer_account import CustomerAccount
from app.domain.models.driver import Driver
from app.domain.models.extracted_field import ExtractedField
from app.domain.models.ledger_entry import LedgerEntry
from app.domain.models.load import Load
from app.domain.models.load_document import LoadDocument
from app.domain.models.notification import Notification
from app.domain.models.onboarding_checklist import OnboardingChecklist
from app.domain.models.organization import Organization
from app.domain.models.payment import Payment
from app.domain.models.payment_method import PaymentMethod
from app.domain.models.referral import Referral
from app.domain.models.service_plan import ServicePlan
from app.domain.models.staff_user import StaffUser
from app.domain.models.subscription import Subscription
from app.domain.models.support_ticket import SupportTicket
from app.domain.models.usage_record import UsageRecord
from app.domain.models.validation_issue import ValidationIssue
from app.domain.models.workflow_event import WorkflowEvent


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()