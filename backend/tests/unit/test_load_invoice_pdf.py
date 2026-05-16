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

    pdf_bytes = _build_professional_invoice_pdf(
        load=load,
        carrier_profile={
            "legal_name": "Blue Sky Transport LLC",
            "email": "billing@bluesky.example",
            "phone": "+1-555-111-2222",
            "address": "100 Main St | Chicago, IL 60601 | USA",
            "mc_number": "MC-778899",
            "dot_number": "DOT-112233",
            "remit_to": (
                "Blue Sky Transport LLC | 100 Main St, Chicago, IL 60601 | "
                "ACH to account ending 2481"
            ),
        },
    )

    assert isinstance(pdf_bytes, bytes)
    assert b"Freight Invoice" in pdf_bytes
    assert b"Invoice #: INV-1001" in pdf_bytes
    assert b"Due Date:" in pdf_bytes
    assert b"Load #: LD-1001" in pdf_bytes
    assert b"Acme Shipper" in pdf_bytes
    assert b"TopLine Broker" in pdf_bytes
    assert b"ap@topline.example" in pdf_bytes
    assert b"1,500.00" in pdf_bytes
    assert b"USD" in pdf_bytes
    assert b"Pickup Date: 2026-04-01" in pdf_bytes
    assert b"Delivery Date: 2026-04-03" in pdf_bytes
    assert b"Required Billing Packet Checklist" in pdf_bytes
    assert b"[X] Rate Confirmation" in pdf_bytes
    assert b"[X] Proof of Delivery" in pdf_bytes
    assert b"[ ] Bill of Lading" in pdf_bytes
    assert b"Total Due" in pdf_bytes
    assert b"Payment / Remittance" in pdf_bytes
    assert b"Remit Instructions:" in pdf_bytes
    assert b"Please reference invoice number and load number with payment." in pdf_bytes
    assert b"Logo: use company letterhead/logo if configured" not in pdf_bytes
    assert b"11111111-2222-3333-4444-555555555555" not in pdf_bytes


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

    pdf_bytes = _build_professional_invoice_pdf(
        load=load,
        carrier_profile={
            "legal_name": "N/A Carrier",
            "email": "N/A",
            "phone": "N/A",
            "address": "N/A",
            "mc_number": "N/A",
            "dot_number": "N/A",
            "remit_to": "N/A",
        },
    )

    assert isinstance(pdf_bytes, bytes)
    assert b"Customer:" in pdf_bytes
    assert b"Not provided" in pdf_bytes


def test_build_professional_invoice_pdf_wraps_long_values_without_crashing() -> None:
    load = SimpleNamespace(
        id=uuid.uuid4(),
        load_number="LD-1099",
        invoice_number="INV-1099",
        rate_confirmation_number="RC-1099-" + "X" * 80,
        customer_account_id=uuid.uuid4(),
        customer_account=SimpleNamespace(
            account_name="Very Long Customer Name " * 6,
            billing_email="billing-team-with-very-long-alias@very-long-customer-domain.example",
        ),
        organization=SimpleNamespace(
            legal_name="Blue Sky Transport LLC",
            name="Blue Sky Transport",
            email="billing@bluesky.example",
            phone="+1-555-111-2222",
            billing_notes="ACH and remit to factoring partner reference " + "9" * 40,
        ),
        broker=SimpleNamespace(
            name="Broker Name " * 6,
            email="accounts-payable-with-extra-long-local-part@broker-domain-with-long-name.example",
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
        notes=("Long note ") * 80,
        documents=[
            SimpleNamespace(document_type=DocumentType.RATE_CONFIRMATION),
            SimpleNamespace(document_type=DocumentType.PROOF_OF_DELIVERY),
        ],
    )

    pdf_bytes = _build_professional_invoice_pdf(
        load=load,
        carrier_profile={
            "legal_name": "N/A Carrier",
            "email": "N/A",
            "phone": "N/A",
            "address": "N/A",
            "mc_number": "N/A",
            "dot_number": "N/A",
            "remit_to": "N/A",
        },
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert b"Bill-To / Broker" in pdf_bytes
    assert b"Shipment Details" in pdf_bytes
    assert b"Load Ref:" in pdf_bytes
    assert b"Notes:" in pdf_bytes


def test_build_professional_invoice_pdf_prefers_load_number_for_load_reference() -> None:
    load = SimpleNamespace(
        id=uuid.UUID("11111111-2222-3333-4444-555555555555"),
        load_number="LD-7777",
        invoice_number="INV-7777",
        rate_confirmation_number=None,
        customer_account_id=uuid.uuid4(),
        customer_account=SimpleNamespace(account_name="Acme Shipper"),
        organization=None,
        broker=None,
        driver=SimpleNamespace(full_name="Jane Driver"),
        gross_amount="1500.00",
        currency_code="USD",
        pickup_location="Chicago, IL",
        pickup_date="2026-04-01",
        delivery_location="Atlanta, GA",
        delivery_date="2026-04-03",
        notes=None,
        documents=[],
        broker_name_raw=None,
        broker_email_raw=None,
    )

    pdf_bytes = _build_professional_invoice_pdf(
        load=load,
        carrier_profile={
            "legal_name": "N/A Carrier",
            "email": "N/A",
            "phone": "N/A",
            "address": "N/A",
            "mc_number": "N/A",
            "dot_number": "N/A",
            "remit_to": "N/A",
        },
    )

    assert b"Load Ref: LD-7777" in pdf_bytes
    assert b"Load Ref: 11111111-2222-3333-4444-555555555555" not in pdf_bytes


def test_build_professional_invoice_pdf_uses_received_checklist_labels_and_preserves_long_remit_text() -> None:
    long_email = "accounts-payable-super-long-local-part@broker-domain-with-long-name.example"
    long_remit = "Remit ACH payments to remit-team-with-long-alias@carrier-payments.example with invoice and load references included"
    load = SimpleNamespace(
        id=uuid.uuid4(),
        load_number="LD-EMAIL",
        invoice_number="INV-EMAIL",
        rate_confirmation_number="RC-EMAIL",
        customer_account_id=uuid.uuid4(),
        customer_account=SimpleNamespace(account_name="Acme Shipper", billing_email=long_email),
        organization=None,
        broker=SimpleNamespace(name="Broker", email=long_email, mc_number="MC-1", payment_terms_days=30),
        driver=SimpleNamespace(full_name="Jane Driver"),
        gross_amount="1500.00",
        currency_code="USD",
        pickup_location="Chicago, IL",
        pickup_date="2026-04-01",
        delivery_location="Atlanta, GA",
        delivery_date="2026-04-03",
        notes="Short note",
        documents=[
            SimpleNamespace(document_type=DocumentType.RATE_CONFIRMATION),
            SimpleNamespace(document_type=DocumentType.BILL_OF_LADING),
            SimpleNamespace(document_type=DocumentType.PROOF_OF_DELIVERY),
        ],
        broker_name_raw=None,
        broker_email_raw=None,
    )

    pdf_bytes = _build_professional_invoice_pdf(
        load=load,
        carrier_profile={
            "legal_name": "Blue Sky Transport LLC",
            "email": "billing-team-with-long-alias@carrier-payments.example",
            "phone": "15551112222",
            "address": "100 Main St | Chicago, IL 60601 | USA",
            "mc_number": "MC-778899",
            "dot_number": "DOT-112233",
            "remit_to": long_remit,
        },
    )

    assert b"Rate Confirmation received" in pdf_bytes
    assert b"Bill of Lading received" in pdf_bytes
    assert b"Proof of Delivery received" in pdf_bytes
    assert b"Invoice generated" in pdf_bytes
    assert b"remit-team-with-long-alias" in pdf_bytes
    assert b"carrier-payments.example" in pdf_bytes
    assert b"\\(555\\) 111-2222" in pdf_bytes or b"+1 \\(555\\) 111-2222" in pdf_bytes
