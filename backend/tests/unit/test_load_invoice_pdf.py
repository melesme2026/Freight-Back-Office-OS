from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.api.v1.loads import _build_professional_invoice_pdf
from app.domain.enums.document_type import DocumentType


def test_build_professional_invoice_pdf_contains_professional_sections() -> None:
    load = SimpleNamespace(
        id=uuid.uuid4(),
        load_number="LD-1001",
        invoice_number="INV-1001",
        rate_confirmation_number="RC-1001",
        customer_account_id=uuid.uuid4(),
        customer_account=SimpleNamespace(account_name="Acme Shipper"),
        organization=SimpleNamespace(
            legal_name="Blue Sky Transport LLC",
            name="Blue Sky Transport",
            email="billing@bluesky.example",
            phone="+1-555-111-2222",
            billing_notes="ACH to account ending 2481",
        ),
        broker=SimpleNamespace(
            name="TopLine Broker",
            email="ap@topline.example",
            mc_number="MC-778899",
            payment_terms_days=30,
        ),
        driver=SimpleNamespace(full_name="Jane Driver"),
        gross_amount="1500.00",
        currency_code="USD",
        pickup_location="Chicago, IL",
        pickup_date="2026-04-01",
        delivery_location="Atlanta, GA",
        delivery_date="2026-04-03",
        notes="Use reference 4432",
        documents=[
            SimpleNamespace(document_type=DocumentType.RATE_CONFIRMATION),
            SimpleNamespace(document_type=DocumentType.PROOF_OF_DELIVERY),
        ],
    )

    pdf_bytes = _build_professional_invoice_pdf(load=load)

    assert isinstance(pdf_bytes, bytes)
    assert b"Freight Invoice" in pdf_bytes
    assert b"Invoice #: INV-1001" in pdf_bytes
    assert b"Load #: LD-1001" in pdf_bytes
    assert b"Acme Shipper" in pdf_bytes
    assert b"TopLine Broker" in pdf_bytes
    assert b"ap@topline.example" in pdf_bytes
    assert b"1,500.00" in pdf_bytes
    assert b"USD" in pdf_bytes
    assert b"Required Billing Packet Checklist" in pdf_bytes
    assert b"[X] Rate Confirmation" in pdf_bytes
    assert b"[X] Proof of Delivery" in pdf_bytes
    assert b"[ ] Bill of Lading" in pdf_bytes
    assert b"Total Due" in pdf_bytes


def test_build_professional_invoice_pdf_handles_missing_optional_fields_without_crashing() -> None:
    customer_account_id = uuid.uuid4()
    load = SimpleNamespace(
        id=uuid.uuid4(),
        load_number="LD-1002",
        customer_account_id=customer_account_id,
        customer_account=None,
        organization=None,
        broker=None,
        driver=None,
        invoice_number=None,
        rate_confirmation_number=None,
        gross_amount="1750.00",
        currency_code="USD",
        pickup_location=None,
        pickup_date=None,
        delivery_location=None,
        delivery_date=None,
        notes=None,
        documents=[],
        broker_name_raw=None,
        broker_email_raw=None,
    )

    pdf_bytes = _build_professional_invoice_pdf(load=load)

    assert isinstance(pdf_bytes, bytes)
    assert str(customer_account_id).encode("latin-1") in pdf_bytes
    assert b"N/A" in pdf_bytes
