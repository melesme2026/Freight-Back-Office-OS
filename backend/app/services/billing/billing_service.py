from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.domain.enums.invoice_status import InvoiceStatus
from app.domain.enums.payment_status import PaymentStatus
from app.domain.enums.subscription_status import SubscriptionStatus
from app.repositories.billing_invoice_repo import BillingInvoiceRepository
from app.repositories.payment_repo import PaymentRepository
from app.repositories.subscription_repo import SubscriptionRepository


class BillingService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.billing_invoice_repo = BillingInvoiceRepository(db)
        self.payment_repo = PaymentRepository(db)
        self.subscription_repo = SubscriptionRepository(db)

    def get_billing_dashboard(
        self,
        *,
        organization_id: str | None = None,
    ) -> dict[str, Any]:
        invoices, _ = self.billing_invoice_repo.list(
            organization_id=organization_id,
            page=1,
            page_size=1000,
            include_related=False,
        )
        payments, _ = self.payment_repo.list(
            organization_id=organization_id,
            page=1,
            page_size=1000,
        )
        subscriptions, _ = self.subscription_repo.list(
            organization_id=organization_id,
            page=1,
            page_size=1000,
            include_related=True,
        )

        open_invoices_count = sum(
            1 for invoice in invoices if invoice.status == InvoiceStatus.OPEN
        )
        past_due_invoices_count = sum(
            1 for invoice in invoices if invoice.status == InvoiceStatus.PAST_DUE
        )
        active_subscriptions_count = sum(
            1
            for subscription in subscriptions
            if subscription.status == SubscriptionStatus.ACTIVE
        )

        now = datetime.now(timezone.utc)
        payments_collected_this_month = Decimal("0.00")
        for payment in payments:
            if payment.status != PaymentStatus.SUCCEEDED:
                continue

            succeeded_at = getattr(payment, "succeeded_at", None)
            if succeeded_at is None:
                continue

            comparison_dt = succeeded_at
            if comparison_dt.tzinfo is None:
                comparison_dt = comparison_dt.replace(tzinfo=timezone.utc)

            if comparison_dt.year == now.year and comparison_dt.month == now.month:
                payments_collected_this_month += Decimal(str(payment.amount))

        mrr_estimate = Decimal("0.00")
        for subscription in subscriptions:
            if subscription.status == SubscriptionStatus.ACTIVE and subscription.service_plan:
                mrr_estimate += Decimal(str(subscription.service_plan.base_price))

        return {
            "mrr_estimate": mrr_estimate.quantize(Decimal("0.01")),
            "open_invoices_count": open_invoices_count,
            "past_due_invoices_count": past_due_invoices_count,
            "payments_collected_this_month": payments_collected_this_month.quantize(
                Decimal("0.01")
            ),
            "active_subscriptions_count": active_subscriptions_count,
        }