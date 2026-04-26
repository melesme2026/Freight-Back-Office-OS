from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from functools import lru_cache
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _build_engine() -> Engine:
    settings = get_settings()
    database_url = settings.database_url

    engine_kwargs: dict[str, Any] = {
        "echo": settings.sqlalchemy_echo,
        "pool_pre_ping": settings.sqlalchemy_pool_pre_ping,
        "future": True,
    }

    if not database_url.startswith("sqlite"):
        engine_kwargs["pool_size"] = settings.sqlalchemy_pool_size
        engine_kwargs["max_overflow"] = settings.sqlalchemy_max_overflow

    return create_engine(
        database_url,
        **engine_kwargs,
    )


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return _build_engine()


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(
        bind=get_engine(),
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        class_=Session,
    )


def get_db() -> Generator[Session, None, None]:
    session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_database_connection() -> tuple[bool, str]:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, "ok"
    except Exception as exc:
        return False, str(exc)


def init_db(import_models: bool = False) -> None:
    """
    Optional local/bootstrap helper.

    Do not rely on this in normal staging/production runtime.
    Schema changes should be applied through Alembic migrations.
    """
    if import_models:
        _import_all_models()
    Base.metadata.create_all(bind=get_engine())


def _import_all_models() -> None:
    from app.domain.models.api_client import ApiClient  # noqa: F401
    from app.domain.models.audit_log import AuditLog  # noqa: F401
    from app.domain.models.billing_invoice import BillingInvoice  # noqa: F401
    from app.domain.models.billing_invoice_line import BillingInvoiceLine  # noqa: F401
    from app.domain.models.broker import Broker  # noqa: F401
    from app.domain.models.customer_account import CustomerAccount  # noqa: F401
    from app.domain.models.driver import Driver  # noqa: F401
    from app.domain.models.extracted_field import ExtractedField  # noqa: F401
    from app.domain.models.follow_up_task import FollowUpTask  # noqa: F401
    from app.domain.models.ledger_entry import LedgerEntry  # noqa: F401
    from app.domain.models.load import Load  # noqa: F401
    from app.domain.models.load_document import LoadDocument  # noqa: F401
    from app.domain.models.notification import Notification  # noqa: F401
    from app.domain.models.onboarding_checklist import OnboardingChecklist  # noqa: F401
    from app.domain.models.organization import Organization  # noqa: F401
    from app.domain.models.payment import Payment  # noqa: F401
    from app.domain.models.payment_method import PaymentMethod  # noqa: F401
    from app.domain.models.referral import Referral  # noqa: F401
    from app.domain.models.service_plan import ServicePlan  # noqa: F401
    from app.domain.models.staff_user import StaffUser  # noqa: F401
    from app.domain.models.submission_event import SubmissionEvent  # noqa: F401
    from app.domain.models.submission_packet import SubmissionPacket  # noqa: F401
    from app.domain.models.submission_packet_document import SubmissionPacketDocument  # noqa: F401
    from app.domain.models.subscription import Subscription  # noqa: F401
    from app.domain.models.support_ticket import SupportTicket  # noqa: F401
    from app.domain.models.usage_record import UsageRecord  # noqa: F401
    from app.domain.models.validation_issue import ValidationIssue  # noqa: F401
    from app.domain.models.workflow_event import WorkflowEvent  # noqa: F401


def metadata_dict() -> dict[str, Any]:
    return {
        "tables": sorted(Base.metadata.tables.keys()),
    }
