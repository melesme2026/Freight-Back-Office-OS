from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import BillingError, NotFoundError
from app.domain.enums.payment_provider import PaymentProvider
from app.domain.enums.payment_status import PaymentStatus
from app.domain.models.payment import Payment
from app.repositories.billing_invoice_repo import BillingInvoiceRepository
from app.repositories.payment_method_repo import PaymentMethodRepository
from app.repositories.payment_repo import PaymentRepository
from app.services.billing.invoice_service import InvoiceService


class PaymentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.payment_repo = PaymentRepository(db)
        self.payment_method_repo = PaymentMethodRepository(db)
        self.billing_invoice_repo = BillingInvoiceRepository(db)
        self.invoice_service = InvoiceService(db)

    def collect_payment(
        self,
        *,
        organization_id: str,
        customer_account_id: str,
        billing_invoice_id: str,
        amount: Decimal,
        payment_method_id: str | None = None,
        driver_id: str | None = None,
        recorded_by_staff_user_id: str | None = None,
    ) -> Payment:
        invoice = self.billing_invoice_repo.get_by_id(billing_invoice_id)
        if invoice is None:
            raise NotFoundError(
                "Invoice not found",
                details={"billing_invoice_id": billing_invoice_id},
            )

        if Decimal(str(invoice.amount_due)) <= Decimal("0.00"):
            raise BillingError(
                "Invoice has no outstanding amount due",
                details={"billing_invoice_id": billing_invoice_id},
            )

        if amount > Decimal(str(invoice.amount_due)):
            raise BillingError(
                "Payment amount exceeds outstanding invoice amount",
                details={
                    "billing_invoice_id": billing_invoice_id,
                    "amount_due": str(invoice.amount_due),
                    "requested_amount": str(amount),
                },
            )

        payment_method = None
        provider = PaymentProvider.MANUAL

        if payment_method_id:
            payment_method = self.payment_method_repo.get_by_id(payment_method_id)
            if payment_method is None:
                raise NotFoundError(
                    "Payment method not found",
                    details={"payment_method_id": payment_method_id},
                )
            provider = payment_method.provider

        now = datetime.now(timezone.utc)

        payment = Payment(
            organization_id=organization_id,
            customer_account_id=customer_account_id,
            billing_invoice_id=billing_invoice_id,
            payment_method_id=payment_method_id,
            driver_id=driver_id,
            recorded_by_staff_user_id=recorded_by_staff_user_id,
            provider=provider,
            provider_payment_id=None,
            status=PaymentStatus.PROCESSING,
            amount=amount,
            currency_code=invoice.currency_code,
            attempted_at=now,
            succeeded_at=None,
            failed_at=None,
            failure_reason=None,
            metadata_json=None,
        )
        payment = self.payment_repo.create(payment)

        payment.status = PaymentStatus.SUCCEEDED
        payment.succeeded_at = now
        payment = self.payment_repo.update(payment)

        self.invoice_service.apply_payment(
            invoice_id=billing_invoice_id,
            amount=amount,
            paid_at=now,
        )

        return payment

    def get_payment(self, payment_id: str) -> Payment:
        payment = self.payment_repo.get_by_id(payment_id)
        if payment is None:
            raise NotFoundError("Payment not found", details={"payment_id": payment_id})
        return payment

    def list_payments(
        self,
        *,
        organization_id: str | None = None,
        customer_account_id: str | None = None,
        billing_invoice_id: str | None = None,
        payment_method_id: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Payment], int]:
        return self.payment_repo.list(
            organization_id=organization_id,
            customer_account_id=customer_account_id,
            billing_invoice_id=billing_invoice_id,
            payment_method_id=payment_method_id,
            status=status,
            page=page,
            page_size=page_size,
        )

    def mark_failed(
        self,
        *,
        payment_id: str,
        failure_reason: str | None = None,
    ) -> Payment:
        payment = self.get_payment(payment_id)
        payment.status = PaymentStatus.FAILED
        payment.failed_at = datetime.now(timezone.utc)
        payment.failure_reason = failure_reason
        return self.payment_repo.update(payment)