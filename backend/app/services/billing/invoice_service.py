from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import BillingError, NotFoundError, ValidationError
from app.domain.enums.invoice_status import InvoiceStatus
from app.domain.models.billing_invoice import BillingInvoice
from app.domain.models.billing_invoice_line import BillingInvoiceLine
from app.repositories.billing_invoice_repo import BillingInvoiceRepository


class InvoiceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.billing_invoice_repo = BillingInvoiceRepository(db)

    def create_invoice(
        self,
        *,
        organization_id: str,
        customer_account_id: str,
        issued_at: Any,
        subscription_id: str | None = None,
        due_at: Any = None,
        billing_period_start: Any = None,
        billing_period_end: Any = None,
        currency_code: str = "USD",
        lines: list[dict[str, Any]] | None = None,
        notes: str | None = None,
    ) -> BillingInvoice:
        normalized_organization_id = self._require_text(
            organization_id,
            field_name="organization_id",
        )
        normalized_customer_account_id = self._require_text(
            customer_account_id,
            field_name="customer_account_id",
        )
        normalized_subscription_id = self._clean_text(subscription_id)
        normalized_currency_code = self._normalize_currency(currency_code)
        normalized_issued_at = self._normalize_datetime(issued_at, field_name="issued_at")
        normalized_due_at = self._normalize_datetime(due_at, field_name="due_at", allow_none=True)
        normalized_period_start = self._normalize_date(
            billing_period_start,
            field_name="billing_period_start",
            allow_none=True,
        )
        normalized_period_end = self._normalize_date(
            billing_period_end,
            field_name="billing_period_end",
            allow_none=True,
        )

        if (
            normalized_period_start is not None
            and normalized_period_end is not None
            and normalized_period_end < normalized_period_start
        ):
            raise ValidationError(
                "billing_period_end cannot be before billing_period_start",
                details={
                    "billing_period_start": str(normalized_period_start),
                    "billing_period_end": str(normalized_period_end),
                },
            )

        invoice_number = self._generate_invoice_number(
            organization_id=normalized_organization_id,
            customer_account_id=normalized_customer_account_id,
        )

        subtotal_amount = Decimal("0.00")
        invoice_lines: list[BillingInvoiceLine] = []

        for index, line in enumerate(lines or [], start=1):
            if not isinstance(line, dict):
                raise ValidationError(
                    "Each invoice line must be an object",
                    details={"line_index": index},
                )

            line_type = self._require_text(line.get("line_type"), field_name=f"lines[{index}].line_type")
            description = self._require_text(
                line.get("description"),
                field_name=f"lines[{index}].description",
            )
            quantity = self._normalize_decimal(
                line.get("quantity", "1"),
                field_name=f"lines[{index}].quantity",
            )
            unit_price = self._normalize_decimal(
                line.get("unit_price", "0"),
                field_name=f"lines[{index}].unit_price",
            )

            if quantity <= Decimal("0"):
                raise ValidationError(
                    "Invoice line quantity must be greater than 0",
                    details={"line_index": index, "quantity": str(quantity)},
                )

            if unit_price < Decimal("0"):
                raise ValidationError(
                    "Invoice line unit_price cannot be negative",
                    details={"line_index": index, "unit_price": str(unit_price)},
                )

            line_total = (quantity * unit_price).quantize(Decimal("0.01"))
            subtotal_amount += line_total

            invoice_lines.append(
                BillingInvoiceLine(
                    line_type=line_type,
                    description=description,
                    quantity=quantity,
                    unit_price=unit_price,
                    line_total=line_total,
                    usage_record_id=self._clean_text(line.get("usage_record_id")),
                    metadata_json=line.get("metadata_json"),
                )
            )

        subtotal_amount = subtotal_amount.quantize(Decimal("0.01"))
        tax_amount = Decimal("0.00")
        total_amount = (subtotal_amount + tax_amount).quantize(Decimal("0.01"))
        amount_paid = Decimal("0.00")
        amount_due = total_amount

        invoice = BillingInvoice(
            organization_id=normalized_organization_id,
            customer_account_id=normalized_customer_account_id,
            subscription_id=normalized_subscription_id,
            invoice_number=invoice_number,
            status=InvoiceStatus.OPEN,
            currency_code=normalized_currency_code,
            subtotal_amount=subtotal_amount,
            tax_amount=tax_amount,
            total_amount=total_amount,
            amount_paid=amount_paid,
            amount_due=amount_due,
            issued_at=normalized_issued_at,
            due_at=normalized_due_at,
            paid_at=None,
            billing_period_start=normalized_period_start,
            billing_period_end=normalized_period_end,
            notes=self._clean_text(notes),
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
        driver_id: str | None = None,
        status: str | None = None,
        due_before: Any = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[BillingInvoice], int]:
        return self.billing_invoice_repo.list(
            organization_id=self._clean_text(organization_id),
            customer_account_id=self._clean_text(customer_account_id),
            subscription_id=self._clean_text(subscription_id),
            driver_id=self._clean_text(driver_id),
            status=self._normalize_status(status, allow_none=True),
            due_before=self._normalize_datetime(due_before, field_name="due_before", allow_none=True),
            page=page,
            page_size=page_size,
        )

    def update_invoice(
        self,
        *,
        invoice_id: str,
        **updates: Any,
    ) -> BillingInvoice:
        invoice = self.get_invoice(invoice_id)

        for field, value in updates.items():
            if not hasattr(invoice, field):
                continue

            if field == "currency_code":
                if value is None:
                    continue
                setattr(invoice, field, self._normalize_currency(value))
            elif field == "status":
                if value is None:
                    continue
                setattr(invoice, field, self._normalize_status(value))
            elif field in {"notes", "subscription_id"}:
                setattr(invoice, field, self._clean_text(value))
            elif field in {"issued_at", "due_at", "paid_at"}:
                setattr(
                    invoice,
                    field,
                    self._normalize_datetime(value, field_name=field, allow_none=True),
                )
            elif field in {"billing_period_start", "billing_period_end"}:
                setattr(
                    invoice,
                    field,
                    self._normalize_date(value, field_name=field, allow_none=True),
                )
            elif field in {"subtotal_amount", "tax_amount", "total_amount", "amount_paid", "amount_due"}:
                if value is None:
                    continue
                setattr(invoice, field, self._normalize_decimal(value, field_name=field))
            elif value is not None:
                setattr(invoice, field, value)

        self._recalculate_totals(invoice)
        updated = self.billing_invoice_repo.update(invoice)
        return self.billing_invoice_repo.get_by_id(updated.id) or updated

    def apply_payment(
        self,
        *,
        invoice_id: str,
        amount: Decimal,
        paid_at: Any = None,
    ) -> BillingInvoice:
        invoice = self.get_invoice(invoice_id)

        payment_amount = self._normalize_decimal(amount, field_name="amount").quantize(Decimal("0.01"))
        if payment_amount <= Decimal("0.00"):
            raise BillingError(
                "Payment amount must be greater than 0",
                details={"invoice_id": invoice_id, "amount": str(payment_amount)},
            )

        current_amount_due = Decimal(str(invoice.amount_due)).quantize(Decimal("0.01"))
        if payment_amount > current_amount_due:
            raise BillingError(
                "Payment amount exceeds outstanding invoice amount",
                details={
                    "invoice_id": invoice_id,
                    "amount_due": str(current_amount_due),
                    "payment_amount": str(payment_amount),
                },
            )

        normalized_paid_at = self._normalize_datetime(
            paid_at,
            field_name="paid_at",
            allow_none=True,
        ) or datetime.utcnow()

        invoice.amount_paid = (Decimal(str(invoice.amount_paid)) + payment_amount).quantize(
            Decimal("0.01")
        )
        invoice.amount_due = (Decimal(str(invoice.total_amount)) - invoice.amount_paid).quantize(
            Decimal("0.01")
        )

        if invoice.amount_due <= Decimal("0.00"):
            invoice.amount_due = Decimal("0.00")
            invoice.status = InvoiceStatus.PAID
            invoice.paid_at = normalized_paid_at
        else:
            invoice.status = InvoiceStatus.OPEN

        updated = self.billing_invoice_repo.update(invoice)
        return self.billing_invoice_repo.get_by_id(updated.id) or updated

    def mark_past_due(self, *, invoice_id: str) -> BillingInvoice:
        invoice = self.get_invoice(invoice_id)
        if invoice.status == InvoiceStatus.OPEN:
            invoice.status = InvoiceStatus.PAST_DUE
        updated = self.billing_invoice_repo.update(invoice)
        return self.billing_invoice_repo.get_by_id(updated.id) or updated

    def _recalculate_totals(self, invoice: BillingInvoice) -> None:
        subtotal = Decimal("0.00")
        for line in invoice.lines:
            quantity = self._normalize_decimal(line.quantity, field_name="line.quantity")
            unit_price = self._normalize_decimal(line.unit_price, field_name="line.unit_price")
            line.line_total = (quantity * unit_price).quantize(Decimal("0.01"))
            subtotal += line.line_total

        invoice.subtotal_amount = subtotal.quantize(Decimal("0.01"))
        invoice.tax_amount = self._normalize_decimal(
            invoice.tax_amount or "0.00",
            field_name="tax_amount",
        ).quantize(Decimal("0.01"))
        invoice.total_amount = (invoice.subtotal_amount + invoice.tax_amount).quantize(
            Decimal("0.01")
        )
        invoice.amount_paid = self._normalize_decimal(
            invoice.amount_paid or "0.00",
            field_name="amount_paid",
        ).quantize(Decimal("0.01"))
        invoice.amount_due = (invoice.total_amount - invoice.amount_paid).quantize(Decimal("0.01"))

        if invoice.amount_due < Decimal("0.00"):
            invoice.amount_due = Decimal("0.00")

    def _generate_invoice_number(
        self,
        *,
        organization_id: str,
        customer_account_id: str,
    ) -> str:
        _, total = self.billing_invoice_repo.list(
            organization_id=organization_id,
            customer_account_id=customer_account_id,
            page=1,
            page_size=1,
        )
        return f"INV-{total + 1001}"

    @staticmethod
    def _clean_text(value: Any) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    def _require_text(self, value: Any, *, field_name: str) -> str:
        cleaned = self._clean_text(value)
        if not cleaned:
            raise ValidationError(
                f"{field_name} is required",
                details={field_name: value},
            )
        return cleaned

    @staticmethod
    def _normalize_decimal(value: Any, *, field_name: str) -> Decimal:
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise ValidationError(
                f"Invalid {field_name}",
                details={field_name: value},
            ) from exc

    @staticmethod
    def _normalize_currency(value: Any) -> str:
        normalized = str(value or "USD").strip().upper()
        if len(normalized) != 3:
            raise ValidationError(
                "Invalid currency_code",
                details={"currency_code": value},
            )
        return normalized

    @staticmethod
    def _normalize_datetime(
        value: Any,
        *,
        field_name: str,
        allow_none: bool = False,
    ) -> datetime | None:
        if value is None or value == "":
            if allow_none:
                return None
            raise ValidationError(
                f"{field_name} is required",
                details={field_name: value},
            )

        if isinstance(value, datetime):
            return value

        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time())

        try:
            return datetime.fromisoformat(str(value).strip())
        except ValueError as exc:
            raise ValidationError(
                f"Invalid {field_name}",
                details={field_name: value},
            ) from exc

    @staticmethod
    def _normalize_date(
        value: Any,
        *,
        field_name: str,
        allow_none: bool = False,
    ) -> date | None:
        if value is None or value == "":
            if allow_none:
                return None
            raise ValidationError(
                f"{field_name} is required",
                details={field_name: value},
            )

        if isinstance(value, date) and not isinstance(value, datetime):
            return value

        if isinstance(value, datetime):
            return value.date()

        try:
            return date.fromisoformat(str(value).strip())
        except ValueError as exc:
            raise ValidationError(
                f"Invalid {field_name}",
                details={field_name: value},
            ) from exc

    @staticmethod
    def _normalize_status(
        value: str | InvoiceStatus | None,
        *,
        allow_none: bool = False,
    ) -> InvoiceStatus | None:
        if value is None:
            if allow_none:
                return None
            raise ValidationError(
                "status is required",
                details={"status": value},
            )

        if isinstance(value, InvoiceStatus):
            return value

        normalized = str(value).strip().lower()
        for status in InvoiceStatus:
            if normalized == status.value.lower():
                return status
            if normalized == status.name.lower():
                return status

        raise ValidationError(
            "Invalid invoice status",
            details={"status": value},
        )
