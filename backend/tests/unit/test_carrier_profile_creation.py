from __future__ import annotations

from app.services.carrier_profile_service import CarrierProfileService


def test_carrier_profile_creation_is_scoped_per_org(db_session) -> None:
    service = CarrierProfileService(db_session)

    org_a = "00000000-0000-0000-0000-000000000901"
    org_b = "00000000-0000-0000-0000-000000000902"

    payload = {
        "legal_name": "Alpha Freight LLC",
        "address_line1": "101 First St",
        "address_line2": None,
        "city": "Dallas",
        "state": "TX",
        "zip": "75001",
        "country": "USA",
        "phone": "+1-555-000-1000",
        "email": "billing@alpha.example",
        "mc_number": "MC-10001",
        "dot_number": "DOT-20001",
        "remit_to_name": "Alpha Freight LLC",
        "remit_to_address": "101 First St, Dallas, TX 75001",
        "remit_to_notes": "Wire preferred",
    }

    created_a = service.upsert_profile(org_a, payload)
    created_b = service.upsert_profile(
        org_b,
        {
            **payload,
            "legal_name": "Bravo Freight LLC",
            "email": "billing@bravo.example",
        },
    )

    assert str(created_a.organization_id) == org_a
    assert str(created_b.organization_id) == org_b
    assert created_a.legal_name == "Alpha Freight LLC"
    assert created_b.legal_name == "Bravo Freight LLC"

    fetched_a = service.get_by_org(org_a)
    fetched_b = service.get_by_org(org_b)
    assert fetched_a is not None
    assert fetched_b is not None
    assert fetched_a.email == "billing@alpha.example"
    assert fetched_b.email == "billing@bravo.example"
