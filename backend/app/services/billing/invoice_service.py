from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.domain.enums.invoice_status import InvoiceStatus
from app.domain.models.billing_invoice import BillingInvoice
from app.domain.models.billing_invoice_line import BillingInvoiceLine
from app.repositories.billing_invoice_repo import BillingInvoiceRepository
from app.repositories.subscription_repo import SubscriptionRepository


class InvoiceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.billing_invoice_repo = BillingInvoiceRepository(db)
        self.subscription_repo = SubscriptionRepository(db)

    def create_invoice(
        self,
        *,
        organization_id: str,
        customer_account_id: str,
        issued_at,
        subscription_id: str | None = None,
        due_at=None,
        billing_period_start=None,
        billing_period_end=None,
        currency_code: str = "USD",
        lines: list[dict] | None = None,
        notes: str | None = None,
    ) -> BillingInvoice:
        invoice_number = self._generate_invoice_number(
            organization_id=organization_id,
            customer_account_id=customer_account_id,
        )

        subtotal_amount = Decimal("0.00")
        invoice_lines: list[BillingInvoiceLine] = []

        for line in lines or []:
            quantity = Decimal(str(line.get("quantity", "1")))
            unit_price = Decimal(str(line.get("unit_price", "0")))
            line_total = (quantity * unit_price).quantize(Decimal("0.01"))

            subtotal_amount += line_total

            invoice_lines.append(
                BillingInvoiceLine(
                    line_type=line["line_type"],
                    description=line["description"],
                    quantity=quantity,
                    unit_price=unit_price,
                    line_total=line_total,
                    usage_record_id=line.get("usage_record_id"),
                    metadata_json=line.get("metadata_json"),
                )
            )

        tax_amount = Decimal("0.00")
        total_amount = subtotal_amount + tax_amount
        amount_paid = Decimal("0.00")
        amount_due = total_amount

        invoice = BillingInvoice(
            organization_id=organization_id,
            customer_account_id=customer_account_id,
            subscription_id=subscription_id,
            invoice_number=invoice_number,
            status=InvoiceStatus.OPEN,
            currency_code=currency_code,
            subtotal_amount=subtotal_amount,
            tax_amount=tax_amount,
            total_amount=total_amount,
            amount_paid=amount_paid,
            amount_due=amount_due,
            issued_at=issued_at,
            due_at=due_at,
            paid_at=None,
            billing_period_start=billing_period_start,
            billing_period_end=billing_period_end,
            notes=notes,
            lines=invoice_lines,
        )
        return self.billing_invoice_repo.create(invoice)

    def get_invoice(self, invoice_id: str) -> BillingInvoice:
        invoice = self.billing_invoice_repo.get_by_id(invoice_id)
        if invoice is None:
            raise NotFoundError("Invoice not found", details={"invoice_id": invoice_id})
        return invoice

    def list_invoices(
        self,
        *,
        organization_id: str | None = None,
        customer_account_id: str | None = None,
        subscription_id: str | None = None,
        status: str | None = None,
        due_before=None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[BillingInvoice], int]:
        return self.billing_invoice_repo.list(
            organization_id=organization_id,
            customer_account_id=customer_account_id,
            subscription_id=subscription_id,
            status=status,
            due_before=due_before,
            page=page,
            page_size=page_size,
        )

    def update_invoice(
        self,
        *,
        invoice_id: str,
        **updates,
    ) -> BillingInvoice:
        invoice = self.get_invoice(invoice_id)

        for field, value in updates.items():
            if hasattr(invoice, field) and value is not None:
                setattr(invoice, field, value)

        self._recalculate_totals(invoice)
        return self.billing_invoice_repo.update(invoice)

    def apply_payment(
        self,
        *,
        invoice_id: str,
        amount: Decimal,
        paid_at=None,
    ) -> BillingInvoice:
        invoice = self.get_invoice(invoice_id)
        invoice.amount_paid = (Decimal(invoice.amount_paid) + amount).quantize(Decimal("0.01"))
        invoice.amount_due = (Decimal(invoice.total_amount) - Decimal(invoice.amount_paid)).quantize(
            Decimal("0.01")
        )

        if invoice.amount_due <= Decimal("0.00"):
            invoice.amount_due = Decimal("0.00")
            invoice.status = InvoiceStatus.PAID
            invoice.paid_at = paid_at
        else:
            invoice.status = InvoiceStatus.OPEN

        return self.billing_invoice_repo.update(invoice)

    def mark_past_due(self, *, invoice_id: str) -> BillingInvoice:
        invoice = self.get_invoice(invoice_id)
        if invoice.status != InvoiceStatus.PAID:
            invoice.status = InvoiceStatus.PAST_DUE
        return self.billing_invoice_repo.update(invoice)

    def _recalculate_totals(self, invoice: BillingInvoice) -> None:
        subtotal = Decimal("0.00")
        for line in invoice.lines:
            quantity = Decimal(str(line.quantity))
            unit_price = Decimal(str(line.unit_price))
            line.line_total = (quantity * unit_price).quantize(Decimal("0.01"))
            subtotal += line.line_total

        invoice.subtotal_amount = subtotal.quantize(Decimal("0.01"))
        invoice.tax_amount = Decimal(str(invoice.tax_amount or "0.00")).quantize(Decimal("0.01"))
        invoice.total_amount = (invoice.subtotal_amount + invoice.tax_amount).quantize(
            Decimal("0.01")
        )
        invoice.amount_paid = Decimal(str(invoice.amount_paid or "0.00")).quantize(Decimal("0.01"))
        invoice.amount_due = (invoice.total_amount - invoice.amount_paid).quantize(Decimal("0.01"))
        if invoice.amount_due < Decimal("0.00"):
            invoice.amount_due = Decimal("0.00")

    def _generate_invoice_number(
        self,
        *,
        organization_id: str,
        customer_account_id: str,
    ) -> str:
        existing, total = self.billing_invoice_repo.list(
            organization_id=organization_id,
            customer_account_id=customer_account_id,
            page=1,
            page_size=1,
        )
        _ = existing
        return f"INV-{total + 1001}"