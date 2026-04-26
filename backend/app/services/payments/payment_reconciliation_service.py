from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.domain.enums.load_payment_status import LoadPaymentStatus
from app.domain.models.load import Load
from app.domain.models.load_payment_record import LoadPaymentRecord
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
        self.db.flush()
        return record

    def mark_paid(self, load_id: str, org_id: str, amount: Decimal | str | float | int, date: datetime | None) -> LoadPaymentRecord:
        record = self.get_or_create_for_load(load_id, org_id)
        record.amount_received = self._decimal(amount)
        record.paid_date = date or datetime.now(timezone.utc)
        record.dispute_reason = None
        record.short_paid_amount = None
        record.payment_status = self.compute_status(record)
        self.db.flush()
        return record

    def mark_partial_payment(self, load_id: str, org_id: str, amount: Decimal | str | float | int) -> LoadPaymentRecord:
        record = self.get_or_create_for_load(load_id, org_id)
        record.amount_received = self._decimal(amount)
        record.short_paid_amount = None
        record.payment_status = LoadPaymentStatus.PARTIALLY_PAID
        self.db.flush()
        return record

    def mark_advance_paid(
        self,
        load_id: str,
        org_id: str,
        amount: Decimal | str | float | int,
        date: datetime | None,
        factor_name: str | None,
    ) -> LoadPaymentRecord:
        record = self.get_or_create_for_load(load_id, org_id)
        record.factoring_used = True
        record.factor_name = self._clean(factor_name)
        record.advance_amount = self._decimal(amount)
        record.advance_date = date or datetime.now(timezone.utc)
        record.payment_status = self.compute_status(record)
        self.db.flush()
        return record

    def mark_reserve_pending(self, load_id: str, org_id: str, reserve_amount: Decimal | str | float | int) -> LoadPaymentRecord:
        record = self.get_or_create_for_load(load_id, org_id)
        record.factoring_used = True
        record.reserve_amount = self._decimal(reserve_amount)
        record.payment_status = self.compute_status(record)
        self.db.flush()
        return record

    def mark_reserve_paid(self, load_id: str, org_id: str, amount: Decimal | str | float | int, date: datetime | None) -> LoadPaymentRecord:
        record = self.get_or_create_for_load(load_id, org_id)
        record.factoring_used = True
        record.reserve_paid_amount = self._decimal(amount)
        record.reserve_paid_date = date or datetime.now(timezone.utc)
        record.payment_status = self.compute_status(record)
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
        self.db.flush()
        return record

    def mark_disputed(self, load_id: str, org_id: str, reason: str) -> LoadPaymentRecord:
        record = self.get_or_create_for_load(load_id, org_id)
        record.dispute_reason = self._clean(reason)
        record.payment_status = self.compute_status(record)
        self.db.flush()
        return record

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
