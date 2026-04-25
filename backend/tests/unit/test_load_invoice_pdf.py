from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.api.v1.loads import _build_simple_invoice_pdf


def test_build_simple_invoice_pdf_uses_customer_relationship_name() -> None:
    load = SimpleNamespace(
        id=uuid.uuid4(),
        load_number="LD-1001",
        customer_account_id=uuid.uuid4(),
        customer_account=SimpleNamespace(account_name="Acme Shipper"),
        gross_amount="1500.00",
        currency_code="USD",
        pickup_location="Chicago, IL",
        pickup_date="2026-04-01",
        delivery_location="Atlanta, GA",
        delivery_date="2026-04-03",
    )

    pdf_bytes = _build_simple_invoice_pdf(load=load)

    assert isinstance(pdf_bytes, bytes)
    assert b"Acme Shipper" in pdf_bytes


def test_build_simple_invoice_pdf_falls_back_to_customer_account_id() -> None:
    customer_account_id = uuid.uuid4()
    load = SimpleNamespace(
        id=uuid.uuid4(),
        load_number="LD-1002",
        customer_account_id=customer_account_id,
        customer_account=None,
        gross_amount="1750.00",
        currency_code="USD",
        pickup_location=None,
        pickup_date=None,
        delivery_location=None,
        delivery_date=None,
    )

    pdf_bytes = _build_simple_invoice_pdf(load=load)

    assert str(customer_account_id).encode("latin-1") in pdf_bytes
