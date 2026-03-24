from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


settings = get_settings()


class Base(DeclarativeBase):
    pass


def _build_engine() -> Engine:
    return create_engine(
        settings.database_url,
        echo=settings.sqlalchemy_echo,
        pool_pre_ping=settings.sqlalchemy_pool_pre_ping,
        pool_size=settings.sqlalchemy_pool_size,
        max_overflow=settings.sqlalchemy_max_overflow,
        future=True,
    )


engine: Engine = _build_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    session = SessionLocal()
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
        with engine.connect() as connection:
            connection.execute("SELECT 1")  # type: ignore[arg-type]
        return True, "ok"
    except Exception as exc:
        return False, str(exc)


def get_engine() -> Engine:
    return engine


def get_session_factory() -> sessionmaker[Session]:
    return SessionLocal


def init_db(import_models: bool = False) -> None:
    if import_models:
        _import_all_models()
    Base.metadata.create_all(bind=engine)


def _import_all_models() -> None:
    from app.domain.models.api_client import ApiClient  # noqa: F401
    from app.domain.models.audit_log import AuditLog  # noqa: F401
    from app.domain.models.billing_invoice import BillingInvoice  # noqa: F401
    from app.domain.models.billing_invoice_line import BillingInvoiceLine  # noqa: F401
    from app.domain.models.broker import Broker  # noqa: F401
    from app.domain.models.customer_account import CustomerAccount  # noqa: F401
    from app.domain.models.driver import Driver  # noqa: F401
    from app.domain.models.extracted_field import ExtractedField  # noqa: F401
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
    from app.domain.models.subscription import Subscription  # noqa: F401
    from app.domain.models.support_ticket import SupportTicket  # noqa: F401
    from app.domain.models.usage_record import UsageRecord  # noqa: F401
    from app.domain.models.validation_issue import ValidationIssue  # noqa: F401
    from app.domain.models.workflow_event import WorkflowEvent  # noqa: F401


def metadata_dict() -> dict[str, Any]:
    return {
        "tables": sorted(Base.metadata.tables.keys()),
    }
    