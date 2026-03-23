from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.core.exceptions import BillingError
from app.services.billing.invoice_service import InvoiceService
from app.services.billing.payment_service import PaymentService


def test_collect_payment_marks_payment_succeeded_and_updates_invoice(db_session) -> None:
    invoice_service = InvoiceService(db_session)
    payment_service = PaymentService(db_session)

    invoice = invoice_service.create_invoice(
        organization_id="00000000-0000-0000-0000-000000000301",
        customer_account_id="00000000-0000-0000-0000-000000000302",
        issued_at=datetime(2026, 5, 10, tzinfo=timezone.utc),
        lines=[
            {
                "line_type": "base_fee",
                "description": "Monthly platform fee",
                "quantity": "1",
                "unit_price": "100.00",
            }
        ],
    )

    payment = payment_service.collect_payment(
        organization_id="00000000-0000-0000-0000-000000000301",
        customer_account_id="00000000-0000-0000-0000-000000000302",
        billing_invoice_id=str(invoice.id),
        amount=Decimal("25.00"),
    )

    assert str(payment.status) == "succeeded"
    assert payment.succeeded_at is not None

    refreshed_invoice = invoice_service.get_invoice(str(invoice.id))
    assert refreshed_invoice.amount_paid == Decimal("25.00")
    assert refreshed_invoice.amount_due == Decimal("75.00")


def test_collect_payment_rejects_overpayment(db_session) -> None:
    invoice_service = InvoiceService(db_session)
    payment_service = PaymentService(db_session)

    invoice = invoice_service.create_invoice(
        organization_id="00000000-0000-0000-0000-000000000311",
        customer_account_id="00000000-0000-0000-0000-000000000312",
        issued_at=datetime(2026, 6, 10, tzinfo=timezone.utc),
        lines=[
            {
                "line_type": "base_fee",
                "description": "Monthly platform fee",
                "quantity": "1",
                "unit_price": "50.00",
            }
        ],
    )

    with pytest.raises(BillingError):
        payment_service.collect_payment(
            organization_id="00000000-0000-0000-0000-000000000311",
            customer_account_id="00000000-0000-0000-0000-000000000312",
            billing_invoice_id=str(invoice.id),
            amount=Decimal("75.00"),
        )


def test_mark_failed_updates_payment_status(db_session) -> None:
    invoice_service = InvoiceService(db_session)
    payment_service = PaymentService(db_session)

    invoice = invoice_service.create_invoice(
        organization_id="00000000-0000-0000-0000-000000000321",
        customer_account_id="00000000-0000-0000-0000-000000000322",
        issued_at=datetime(2026, 7, 10, tzinfo=timezone.utc),
        lines=[
            {
                "line_type": "base_fee",
                "description": "Monthly platform fee",
                "quantity": "1",
                "unit_price": "80.00",
            }
        ],
    )

    payment = payment_service.collect_payment(
        organization_id="00000000-0000-0000-0000-000000000321",
        customer_account_id="00000000-0000-0000-0000-000000000322",
        billing_invoice_id=str(invoice.id),
        amount=Decimal("20.00"),
    )

    failed = payment_service.mark_failed(
        payment_id=str(payment.id),
        failure_reason="manual reversal for test",
    )

    assert str(failed.status) == "failed"
    assert failed.failed_at is not None
    assert failed.failure_reason == "manual reversal for test"