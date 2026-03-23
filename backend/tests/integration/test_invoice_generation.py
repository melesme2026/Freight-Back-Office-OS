from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from app.services.billing.invoice_service import InvoiceService


def test_invoice_generation_with_multiple_lines(db_session) -> None:
    service = InvoiceService(db_session)

    invoice = service.create_invoice(
        organization_id="00000000-0000-0000-0000-000000000801",
        customer_account_id="00000000-0000-0000-0000-000000000802",
        issued_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        currency_code="USD",
        lines=[
            {
                "line_type": "subscription",
                "description": "Monthly subscription",
                "quantity": "1",
                "unit_price": "99.00",
            },
            {
                "line_type": "usage",
                "description": "Per-load billing",
                "quantity": "3",
                "unit_price": "12.50",
            },
        ],
        notes="September invoice",
    )

    assert invoice.invoice_number.startswith("INV-")
    assert invoice.subtotal_amount == Decimal("136.50")
    assert invoice.total_amount == Decimal("136.50")
    assert invoice.amount_due == Decimal("136.50")
    assert invoice.notes == "September invoice"
    assert len(invoice.lines) == 2


def test_invoice_generation_and_partial_payment_flow(db_session) -> None:
    service = InvoiceService(db_session)

    invoice = service.create_invoice(
        organization_id="00000000-0000-0000-0000-000000000811",
        customer_account_id="00000000-0000-0000-0000-000000000812",
        issued_at=datetime(2026, 9, 15, tzinfo=timezone.utc),
        lines=[
            {
                "line_type": "subscription",
                "description": "Monthly subscription",
                "quantity": "1",
                "unit_price": "120.00",
            }
        ],
    )

    updated = service.apply_payment(
        invoice_id=str(invoice.id),
        amount=Decimal("20.00"),
        paid_at=datetime(2026, 9, 16, tzinfo=timezone.utc),
    )

    assert updated.amount_paid == Decimal("20.00")
    assert updated.amount_due == Decimal("100.00")
    assert str(updated.status) == "open"