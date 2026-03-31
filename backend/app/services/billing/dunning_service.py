from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.domain.enums.invoice_status import InvoiceStatus
from app.repositories.billing_invoice_repo import BillingInvoiceRepository


class DunningService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.billing_invoice_repo = BillingInvoiceRepository(db)

    def find_past_due_invoices(
        self,
        *,
        organization_id: str | None = None,
        as_of: datetime | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> tuple[list[Any], int]:
        effective_as_of = as_of or datetime.now(timezone.utc)

        return self.billing_invoice_repo.list(
            organization_id=organization_id,
            status=InvoiceStatus.OPEN,
            due_before=effective_as_of,
            page=page,
            page_size=page_size,
        )

    def mark_past_due(
        self,
        *,
        organization_id: str | None = None,
        as_of: datetime | None = None,
    ) -> dict[str, int]:
        invoices, _ = self.find_past_due_invoices(
            organization_id=organization_id,
            as_of=as_of,
            page=1,
            page_size=10000,
        )

        updated = 0

        for invoice in invoices:
            if invoice.status == InvoiceStatus.OPEN:
                invoice.status = InvoiceStatus.PAST_DUE
                self.billing_invoice_repo.update(invoice)
                updated += 1

        return {
            "updated_count": updated,
        }