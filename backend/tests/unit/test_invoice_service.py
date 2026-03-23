from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from app.services.billing.invoice_service import InvoiceService


def test_create_invoice_calculates_totals(db_session) -> None:
    service = InvoiceService(db_session)

    item = service.create_invoice(
        organization_id="00000000-0000-0000-0000-000000000201",
        customer_account_id="00000000-0000-0000-0000-000000000202",
        issued_at=datetime(2026, 1, 10, tzinfo=timezone.utc),
        currency_code="USD",
        lines=[
            {
                "line_type": "base_fee",
                "description": "Monthly platform fee",
                "quantity": "1",
                "unit_price": "99.00",
            },
            {
                "line_type": "usage",
                "description": "Per load usage",
                "quantity": "2",
                "unit_price": "10.50",
            },
        ],
    )

    assert item.invoice_number.startswith("INV-")
    assert item.subtotal_amount == Decimal("120.00")
    assert item.tax_amount == Decimal("0.00")
    assert item.total_amount == Decimal("120.00")
    assert item.amount_due == Decimal("120.00")
    assert len(item.lines) == 2


def test_apply_payment_reduces_amount_due(db_session) -> None:
    service = InvoiceService(db_session)

    item = service.create_invoice(
        organization_id="00000000-0000-0000-0000-000000000211",
        customer_account_id="00000000-0000-0000-0000-000000000212",
        issued_at=datetime(2026, 2, 10, tzinfo=timezone.utc),
        lines=[
            {
                "line_type": "base_fee",
                "description": "Monthly platform fee",
                "quantity": "1",
                "unit_price": "100.00",
            }
        ],
    )

    updated = service.apply_payment(
        invoice_id=str(item.id),
        amount=Decimal("40.00"),
        paid_at=datetime(2026, 2, 11, tzinfo=timezone.utc),
    )

    assert updated.amount_paid == Decimal("40.00")
    assert updated.amount_due == Decimal("60.00")
    assert str(updated.status) == "open"


def test_apply_payment_marks_invoice_paid_when_fully_paid(db_session) -> None:
    service = InvoiceService(db_session)

    item = service.create_invoice(
        organization_id="00000000-0000-0000-0000-000000000221",
        customer_account_id="00000000-0000-0000-0000-000000000222",
        issued_at=datetime(2026, 3, 10, tzinfo=timezone.utc),
        lines=[
            {
                "line_type": "base_fee",
                "description": "Monthly platform fee",
                "quantity": "1",
                "unit_price": "75.00",
            }
        ],
    )

    updated = service.apply_payment(
        invoice_id=str(item.id),
        amount=Decimal("75.00"),
        paid_at=datetime(2026, 3, 11, tzinfo=timezone.utc),
    )

    assert updated.amount_paid == Decimal("75.00")
    assert updated.amount_due == Decimal("0.00")
    assert str(updated.status) == "paid"
    assert updated.paid_at is not None


def test_mark_past_due_updates_status(db_session) -> None:
    service = InvoiceService(db_session)

    item = service.create_invoice(
        organization_id="00000000-0000-0000-0000-000000000231",
        customer_account_id="00000000-0000-0000-0000-000000000232",
        issued_at=datetime(2026, 4, 10, tzinfo=timezone.utc),
        lines=[
            {
                "line_type": "base_fee",
                "description": "Monthly platform fee",
                "quantity": "1",
                "unit_price": "55.00",
            }
        ],
    )

    updated = service.mark_past_due(invoice_id=str(item.id))

    assert str(updated.status) == "past_due"