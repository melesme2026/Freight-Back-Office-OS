from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

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
        )

        open_invoices_count = sum(1 for invoice in invoices if str(invoice.status) == "open")
        past_due_invoices_count = sum(
            1 for invoice in invoices if str(invoice.status) == "past_due"
        )
        active_subscriptions_count = sum(
            1 for subscription in subscriptions if str(subscription.status) == "active"
        )

        payments_collected_this_month = Decimal("0.00")
        for payment in payments:
            if str(payment.status) == "succeeded":
                payments_collected_this_month += payment.amount

        mrr_estimate = Decimal("0.00")
        for subscription in subscriptions:
            if str(subscription.status) == "active" and subscription.service_plan:
                mrr_estimate += subscription.service_plan.base_price

        return {
            "mrr_estimate": mrr_estimate,
            "open_invoices_count": open_invoices_count,
            "past_due_invoices_count": past_due_invoices_count,
            "payments_collected_this_month": payments_collected_this_month,
            "active_subscriptions_count": active_subscriptions_count,
        }