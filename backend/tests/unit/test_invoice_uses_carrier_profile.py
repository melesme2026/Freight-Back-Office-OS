from __future__ import annotations

from app.api.v1.loads import _generate_and_persist_invoice_pdf
from app.core.exceptions import ValidationError
from app.domain.enums.document_type import DocumentType
from app.services.carrier_profile_service import CarrierProfileService
from app.services.documents.document_service import DocumentService
from app.services.loads.load_service import LoadService


def _seed_load(db_session):
    load = LoadService(db_session).create_load(
        organization_id="00000000-0000-0000-0000-000000000951",
        customer_account_id="00000000-0000-0000-0000-000000000952",
        driver_id="00000000-0000-0000-0000-000000000953",
        load_number="LOAD-951",
    )
    DocumentService(db_session).create_document(
        organization_id=str(load.organization_id),
        customer_account_id=str(load.customer_account_id),
        driver_id=str(load.driver_id),
        load_id=str(load.id),
        document_type=DocumentType.RATE_CONFIRMATION,
        source_channel="manual",
        storage_key="uploads/rc-951.pdf",
        original_filename="rc-951.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
    )
    return load


def test_invoice_uses_carrier_profile_fields_and_invoice_number(db_session) -> None:
    load = _seed_load(db_session)
    CarrierProfileService(db_session).upsert_profile(
        str(load.organization_id),
        {
            "legal_name": "Carrier Prime LLC",
            "address_line1": "44 Harbor Way",
            "address_line2": "Suite 9",
            "city": "Savannah",
            "state": "GA",
            "zip": "31401",
            "country": "USA",
            "phone": "+1-555-444-8989",
            "email": "billing@carrierprime.example",
            "mc_number": "MC-445566",
            "dot_number": "DOT-889900",
            "remit_to_name": "Carrier Prime LLC",
            "remit_to_address": "44 Harbor Way, Suite 9, Savannah, GA 31401",
            "remit_to_notes": "ACH remittance with load reference",
        },
    )

    pdf = _generate_and_persist_invoice_pdf(db=db_session, load=load)

    assert b"Carrier Prime LLC" in pdf
    assert b"MC: MC-445566" in pdf
    assert b"DOT: DOT-889900" in pdf
    assert b"Remit Instructions:" in pdf
    assert load.invoice_number is not None
    assert load.invoice_number.startswith("INV-")


def test_invoice_generation_fails_when_carrier_profile_missing(db_session) -> None:
    load = _seed_load(db_session)

    try:
        _generate_and_persist_invoice_pdf(db=db_session, load=load)
    except ValidationError as exc:
        assert "Complete Carrier Profile before generating invoice" in str(exc)
    else:
        raise AssertionError("Expected ValidationError when carrier profile is missing")


def test_invoice_generation_fails_with_structured_missing_fields_when_profile_incomplete(db_session) -> None:
    load = _seed_load(db_session)
    profile = CarrierProfileService(db_session).upsert_profile(
        str(load.organization_id),
        {
            "legal_name": "Carrier Prime LLC",
            "address_line1": "123 Main St",
            "address_line2": "",
            "city": "Dallas",
            "state": "TX",
            "zip": "75001",
            "country": "USA",
            "phone": "+1-555-333-2222",
            "email": "billing@example.com",
            "mc_number": "",
            "dot_number": "",
            "remit_to_name": "Carrier Prime LLC",
            "remit_to_address": "123 Main St, Dallas, TX",
            "remit_to_notes": "",
        },
    )
    profile.address_line1 = ""
    profile.city = " "
    profile.state = ""
    profile.zip = ""
    profile.phone = ""
    profile.email = ""
    profile.remit_to_name = ""
    profile.remit_to_address = ""
    db_session.add(profile)
    db_session.commit()

    try:
        _generate_and_persist_invoice_pdf(db=db_session, load=load)
    except ValidationError as exc:
        assert exc.details["code"] == "carrier_profile_incomplete"
        assert exc.details["action_url"] == "/dashboard/settings/carrier-profile"
        assert set(exc.details["missing_fields"]) == {
            "address_line1",
            "city",
            "state",
            "postal_code",
            "phone",
            "email",
            "remit_to_name",
            "remit_to_address",
        }
    else:
        raise AssertionError("Expected ValidationError when carrier profile is incomplete")
