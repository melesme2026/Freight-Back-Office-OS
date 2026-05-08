from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.domain.enums.load_payment_status import LoadPaymentStatus
from app.domain.enums.factoring import FactoringAgingBucket, FactoringReconciliationStatus, FactoringWorkflowStatus
from app.domain.models.load import Load
from app.domain.models.load_payment_record import LoadPaymentRecord
from app.domain.models.factoring_company import FactoringCompany
from app.services.loads.load_service import LoadService


class PaymentReconciliationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.load_service = LoadService(db)

    def get_or_create_for_load(self, load_id: str, org_id: str, actor_staff_user_id: str | None = None) -> LoadPaymentRecord:
        load = self._get_load(load_id=load_id, org_id=org_id)
        stmt = select(LoadPaymentRecord).where(
            LoadPaymentRecord.load_id == load.id,
            LoadPaymentRecord.organization_id == load.organization_id,
        )
        record = self.db.scalar(stmt)
        if record is not None:
            return record

        gross_amount = self._decimal(load.gross_amount)
        record = LoadPaymentRecord(
            organization_id=load.organization_id,
            load_id=load.id,
            gross_amount=gross_amount,
            expected_amount=gross_amount,
            amount_received=Decimal("0"),
            currency=(load.currency_code or "USD").upper(),
            payment_status=LoadPaymentStatus.NOT_SUBMITTED,
            factoring_status=FactoringWorkflowStatus.NOT_FACTORED,
            reconciliation_status=FactoringReconciliationStatus.UNRECONCILED,
            created_by_staff_user_id=self._optional_uuid(actor_staff_user_id),
            updated_by_staff_user_id=self._optional_uuid(actor_staff_user_id),
        )
        self.db.add(record)
        self.db.flush()
        return record

    def update_amount_received(self, load_id: str, org_id: str, amount: Decimal | str | float | int) -> LoadPaymentRecord:
        record = self.get_or_create_for_load(load_id, org_id)
        record.amount_received = self._decimal(amount)
        record.payment_status = self.compute_status(record)
        record.reconciliation_status = self.compute_reconciliation_status(record)
        record.factoring_status = self.compute_factoring_status(record)
        self.db.flush()
        return record

    def mark_paid(self, load_id: str, org_id: str, amount: Decimal | str | float | int, date: datetime | None) -> LoadPaymentRecord:
        record = self.get_or_create_for_load(load_id, org_id)
        record.amount_received = self._decimal(amount)
        record.paid_date = date or datetime.now(timezone.utc)
        record.dispute_reason = None
        record.short_paid_amount = None
        record.payment_status = self.compute_status(record)
        record.reconciliation_status = self.compute_reconciliation_status(record)
        record.factoring_status = self.compute_factoring_status(record)
        self.db.flush()
        return record

    def mark_partial_payment(self, load_id: str, org_id: str, amount: Decimal | str | float | int) -> LoadPaymentRecord:
        record = self.get_or_create_for_load(load_id, org_id)
        record.amount_received = self._decimal(amount)
        record.short_paid_amount = None
        record.payment_status = LoadPaymentStatus.PARTIALLY_PAID
        record.reconciliation_status = FactoringReconciliationStatus.PARTIALLY_RECONCILED
        record.factoring_status = FactoringWorkflowStatus.PARTIALLY_PAID
        self.db.flush()
        return record

    def mark_advance_paid(
        self,
        load_id: str,
        org_id: str,
        amount: Decimal | str | float | int,
        date: datetime | None,
        factor_name: str | None,
        factoring_company_id: str | None = None,
        factoring_fee_percent: Decimal | str | float | int | None = None,
        factoring_fee_amount: Decimal | str | float | int | None = None,
        reserve_amount: Decimal | str | float | int | None = None,
        notes: str | None = None,
    ) -> LoadPaymentRecord:
        record = self.get_or_create_for_load(load_id, org_id)
        record.factoring_used = True
        self._assign_factoring_company(record, factoring_company_id)
        record.factor_name = self._clean(factor_name) or record.factor_name
        record.advance_amount = self._decimal(amount)
        record.advance_date = date or datetime.now(timezone.utc)
        if factoring_fee_percent is not None:
            record.factoring_fee_percent = self._decimal(factoring_fee_percent)
        if factoring_fee_amount is not None:
            record.factoring_fee_amount = self._decimal(factoring_fee_amount)
        elif record.factoring_fee_percent is not None:
            record.factoring_fee_amount = self.calculate_percent_amount(record.expected_amount, record.factoring_fee_percent)
        if reserve_amount is not None:
            record.reserve_amount = self._decimal(reserve_amount)
        if notes is not None:
            record.factoring_notes = self._clean(notes)
        record.payment_status = self.compute_status(record)
        record.reconciliation_status = self.compute_reconciliation_status(record)
        record.factoring_status = self.compute_factoring_status(record)
        self.db.flush()
        return record

    def mark_reserve_pending(self, load_id: str, org_id: str, reserve_amount: Decimal | str | float | int) -> LoadPaymentRecord:
        record = self.get_or_create_for_load(load_id, org_id)
        record.factoring_used = True
        record.reserve_amount = self._decimal(reserve_amount)
        record.payment_status = self.compute_status(record)
        record.reconciliation_status = self.compute_reconciliation_status(record)
        record.factoring_status = self.compute_factoring_status(record)
        self.db.flush()
        return record

    def mark_reserve_paid(self, load_id: str, org_id: str, amount: Decimal | str | float | int, date: datetime | None) -> LoadPaymentRecord:
        record = self.get_or_create_for_load(load_id, org_id)
        record.factoring_used = True
        record.reserve_paid_amount = self._decimal(amount)
        record.reserve_paid_date = date or datetime.now(timezone.utc)
        record.payment_status = self.compute_status(record)
        record.reconciliation_status = self.compute_reconciliation_status(record)
        record.factoring_status = self.compute_factoring_status(record)
        self.db.flush()
        return record

    def mark_short_paid(
        self,
        load_id: str,
        org_id: str,
        received_amount: Decimal | str | float | int,
        expected_amount: Decimal | str | float | int,
        reason: str | None,
    ) -> LoadPaymentRecord:
        record = self.get_or_create_for_load(load_id, org_id)
        record.amount_received = self._decimal(received_amount)
        record.expected_amount = self._decimal(expected_amount)
        record.short_paid_amount = max(record.expected_amount - record.amount_received, Decimal("0"))
        record.dispute_reason = self._clean(reason)
        record.payment_status = LoadPaymentStatus.SHORT_PAID
        record.reconciliation_status = FactoringReconciliationStatus.PARTIALLY_RECONCILED
        record.factoring_status = FactoringWorkflowStatus.DISPUTED
        self.db.flush()
        return record

    def mark_disputed(self, load_id: str, org_id: str, reason: str) -> LoadPaymentRecord:
        record = self.get_or_create_for_load(load_id, org_id)
        record.dispute_reason = self._clean(reason)
        record.payment_status = self.compute_status(record)
        record.reconciliation_status = self.compute_reconciliation_status(record)
        record.factoring_status = self.compute_factoring_status(record)
        self.db.flush()
        return record

    def assign_factoring(
        self,
        load_id: str,
        org_id: str,
        *,
        factoring_company_id: str | None,
        factor_name: str | None,
        reserve_percent: Decimal | str | float | int | None = None,
        fee_percent: Decimal | str | float | int | None = None,
        notes: str | None = None,
    ) -> LoadPaymentRecord:
        record = self.get_or_create_for_load(load_id, org_id)
        record.factoring_used = True
        self._assign_factoring_company(record, factoring_company_id)
        record.factor_name = self._clean(factor_name) or record.factor_name
        if reserve_percent is not None:
            record.reserve_amount = self.calculate_percent_amount(record.expected_amount, self._decimal(reserve_percent))
        if fee_percent is not None:
            record.factoring_fee_percent = self._decimal(fee_percent)
            record.factoring_fee_amount = self.calculate_percent_amount(record.expected_amount, record.factoring_fee_percent)
        if notes is not None:
            record.factoring_notes = self._clean(notes)
        record.payment_status = LoadPaymentStatus.SUBMITTED
        record.factoring_status = FactoringWorkflowStatus.SUBMITTED_TO_FACTORING
        record.reconciliation_status = self.compute_reconciliation_status(record)
        self.db.flush()
        return record

    def set_reconciliation_status(self, load_id: str, org_id: str, status: str) -> LoadPaymentRecord:
        record = self.get_or_create_for_load(load_id, org_id)
        record.reconciliation_status = FactoringReconciliationStatus(status)
        if record.reconciliation_status == FactoringReconciliationStatus.RECONCILED:
            record.factoring_status = FactoringWorkflowStatus.RECONCILED
        self.db.flush()
        return record

    def calculate_percent_amount(self, amount: Decimal | str | float | int | None, percent: Decimal | str | float | int | None) -> Decimal:
        return (self._decimal(amount) * self._decimal(percent) / Decimal("100")).quantize(Decimal("0.01"))

    def reserve_pending_amount(self, record: LoadPaymentRecord) -> Decimal:
        return max(self._decimal(record.reserve_amount) - self._decimal(record.reserve_paid_amount), Decimal("0"))

    def compute_reconciliation_status(self, record: LoadPaymentRecord) -> FactoringReconciliationStatus:
        expected_amount = self._decimal(record.expected_amount)
        amount_received = self._decimal(record.amount_received)
        if expected_amount > Decimal("0") and amount_received >= expected_amount and self.reserve_pending_amount(record) == Decimal("0"):
            return FactoringReconciliationStatus.RECONCILED
        if amount_received > Decimal("0") or self._decimal(record.advance_amount) > Decimal("0") or self._decimal(record.reserve_paid_amount) > Decimal("0"):
            return FactoringReconciliationStatus.PARTIALLY_RECONCILED
        return FactoringReconciliationStatus.UNRECONCILED

    def compute_factoring_status(self, record: LoadPaymentRecord) -> FactoringWorkflowStatus:
        if self._clean(record.dispute_reason):
            return FactoringWorkflowStatus.DISPUTED
        if not bool(record.factoring_used):
            return FactoringWorkflowStatus.NOT_FACTORED
        if self.compute_reconciliation_status(record) == FactoringReconciliationStatus.RECONCILED:
            return FactoringWorkflowStatus.RECONCILED
        if self.reserve_pending_amount(record) > Decimal("0"):
            return FactoringWorkflowStatus.RESERVE_PENDING
        if self._decimal(record.amount_received) > Decimal("0") and self._decimal(record.amount_received) < self._decimal(record.expected_amount):
            return FactoringWorkflowStatus.PARTIALLY_PAID
        if self._decimal(record.advance_amount) > Decimal("0"):
            return FactoringWorkflowStatus.FUNDED
        return FactoringWorkflowStatus.SUBMITTED_TO_FACTORING

    def aging_bucket(self, record: LoadPaymentRecord, now: datetime | None = None) -> FactoringAgingBucket:
        baseline = getattr(record, "advance_date", None) or getattr(record.load, "submitted_at", None) or getattr(record.load, "delivery_date", None) or record.created_at
        if baseline is None:
            return FactoringAgingBucket.CURRENT
        current = now or datetime.now(timezone.utc)
        if not isinstance(baseline, datetime):
            baseline = datetime.combine(baseline, datetime.min.time(), tzinfo=timezone.utc)
        elif baseline.tzinfo is None:
            baseline = baseline.replace(tzinfo=timezone.utc)
        days = max((current - baseline).days, 0)
        if days == 0:
            return FactoringAgingBucket.CURRENT
        if days <= 15:
            return FactoringAgingBucket.DAYS_1_15
        if days <= 30:
            return FactoringAgingBucket.DAYS_16_30
        if days <= 60:
            return FactoringAgingBucket.DAYS_31_60
        return FactoringAgingBucket.DAYS_60_PLUS

    def list_factoring_dashboard(self, org_id: str) -> list[LoadPaymentRecord]:
        stmt = (
            select(LoadPaymentRecord)
            .where(LoadPaymentRecord.organization_id == uuid.UUID(str(org_id)))
            .where(LoadPaymentRecord.factoring_used.is_(True))
            .order_by(LoadPaymentRecord.updated_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def compute_status(self, record: LoadPaymentRecord) -> LoadPaymentStatus:
        if self._clean(record.dispute_reason):
            return LoadPaymentStatus.DISPUTED

        expected_amount = self._decimal(record.expected_amount)
        amount_received = self._decimal(record.amount_received)
        reserve_amount = self._decimal(record.reserve_amount)
        reserve_paid_amount = self._decimal(record.reserve_paid_amount)
        advance_amount = self._decimal(record.advance_amount)

        if getattr(record, "payment_status", None) == LoadPaymentStatus.SHORT_PAID:
            return LoadPaymentStatus.SHORT_PAID

        if amount_received >= expected_amount and expected_amount > Decimal("0"):
            return LoadPaymentStatus.PAID

        if bool(record.factoring_used) and reserve_amount > reserve_paid_amount:
            return LoadPaymentStatus.RESERVE_PENDING

        if bool(record.factoring_used) and advance_amount > Decimal("0"):
            return LoadPaymentStatus.ADVANCE_PAID

        if amount_received > Decimal("0") and amount_received < expected_amount:
            return LoadPaymentStatus.PARTIALLY_PAID

        if amount_received <= Decimal("0"):
            return LoadPaymentStatus.AWAITING_PAYMENT

        return LoadPaymentStatus.NOT_SUBMITTED

    def _get_load(self, *, load_id: str, org_id: str) -> Load:
        load = self.load_service.get_load(load_id)
        if str(load.organization_id) != str(org_id):
            raise NotFoundError("Load not found", details={"load_id": load_id})
        return load

    def _assign_factoring_company(self, record: LoadPaymentRecord, factoring_company_id: str | None) -> None:
        if not factoring_company_id:
            return
        company = self.db.get(FactoringCompany, uuid.UUID(str(factoring_company_id)))
        if company is None or str(company.organization_id) != str(record.organization_id):
            raise NotFoundError("Factoring company not found", details={"factoring_company_id": factoring_company_id})
        record.factoring_company_id = company.id
        record.factor_name = company.company_name
        if record.reserve_amount is None and company.default_reserve_percent:
            record.reserve_amount = self.calculate_percent_amount(record.expected_amount, company.default_reserve_percent)
        if record.factoring_fee_percent is None and company.default_fee_percent:
            record.factoring_fee_percent = company.default_fee_percent
            record.factoring_fee_amount = self.calculate_percent_amount(record.expected_amount, company.default_fee_percent)

    def _optional_uuid(self, value: str | None) -> uuid.UUID | None:
        if not value:
            return None
        return uuid.UUID(str(value))

    def _clean(self, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    def _decimal(self, value: Decimal | str | float | int | None) -> Decimal:
        if value is None:
            return Decimal("0")
        return Decimal(str(value))
