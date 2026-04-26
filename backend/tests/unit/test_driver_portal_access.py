from __future__ import annotations

import asyncio
from io import BytesIO

import pytest
from starlette.datastructures import UploadFile

from app.api.v1.documents import upload_driver_document
from app.api.v1.load_payment_reconciliation import _authorize_payment_read, _authorize_payment_write
from app.api.v1.loads import _authorize_load_access, _authorize_submission_download, _authorize_submission_read
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.domain.models.driver import Driver
from app.services.loads.load_service import LoadService


def _seed_load(db_session, *, organization_id: str, driver_id: str, load_number: str):
    return LoadService(db_session).create_load(
        organization_id=organization_id,
        customer_account_id="00000000-0000-0000-0000-000000009902",
        driver_id=driver_id,
        load_number=load_number,
        pickup_location="Chicago, IL",
        delivery_location="Atlanta, GA",
    )


def _seed_driver(db_session, *, organization_id: str, driver_id: str) -> None:
    db_session.add(
        Driver(
            id=driver_id,
            organization_id=organization_id,
            customer_account_id="00000000-0000-0000-0000-000000009902",
            full_name=f"Driver {driver_id[-4:]}",
            phone=f"555{driver_id[-4:]}",
            email=None,
            is_active=True,
        )
    )
    db_session.flush()


def test_driver_only_load_visibility(db_session) -> None:
    org_id = "00000000-0000-0000-0000-000000010001"
    driver_a = "00000000-0000-0000-0000-000000010011"
    driver_b = "00000000-0000-0000-0000-000000010022"

    _seed_driver(db_session, organization_id=org_id, driver_id=driver_a)
    _seed_driver(db_session, organization_id=org_id, driver_id=driver_b)
    _seed_load(db_session, organization_id=org_id, driver_id=driver_a, load_number="LD-A")
    _seed_load(db_session, organization_id=org_id, driver_id=driver_b, load_number="LD-B")

    items, total = LoadService(db_session).list_loads(
        organization_id=org_id,
        driver_id=driver_a,
        page=1,
        page_size=50,
    )

    assert total == 1
    assert len(items) == 1
    assert str(items[0].driver_id) == driver_a


def test_cross_driver_access_denied(db_session) -> None:
    org_id = "00000000-0000-0000-0000-000000010101"
    driver_a = "00000000-0000-0000-0000-000000010111"
    driver_b = "00000000-0000-0000-0000-000000010122"

    _seed_driver(db_session, organization_id=org_id, driver_id=driver_a)
    _seed_driver(db_session, organization_id=org_id, driver_id=driver_b)
    other_driver_load = _seed_load(db_session, organization_id=org_id, driver_id=driver_b, load_number="LD-OTHER")

    with pytest.raises(UnauthorizedError):
        _authorize_load_access(
            item=other_driver_load,
            token_payload={"organization_id": org_id, "role": "driver", "driver_id": driver_a},
        )


def test_upload_restricted_to_assigned_load(db_session) -> None:
    org_id = "00000000-0000-0000-0000-000000010201"
    driver_a = "00000000-0000-0000-0000-000000010211"
    driver_b = "00000000-0000-0000-0000-000000010222"

    _seed_driver(db_session, organization_id=org_id, driver_id=driver_a)
    _seed_driver(db_session, organization_id=org_id, driver_id=driver_b)
    target_load = _seed_load(db_session, organization_id=org_id, driver_id=driver_b, load_number="LD-NOT-MINE")

    with pytest.raises(UnauthorizedError):
        asyncio.run(
            upload_driver_document(
                organization_id=org_id,
                token_payload={
                    "organization_id": org_id,
                    "role": "driver",
                    "driver_id": driver_a,
                    "sub": driver_a,
                },
                file=UploadFile(
                    filename="pod.pdf",
                    file=BytesIO(b"pdf-content"),
                    headers={"content-type": "application/pdf"},
                ),
                document_type="proof_of_delivery",
                load_id=target_load.id,
                db=db_session,
            )
        )


def test_driver_cannot_access_money_or_submission_endpoints(db_session) -> None:
    with pytest.raises(ForbiddenError):
        _authorize_payment_read({"role": "driver"})

    with pytest.raises(ForbiddenError):
        _authorize_payment_write({"role": "driver"})

    with pytest.raises(ForbiddenError):
        _authorize_submission_read({"role": "driver"})

    load = _seed_load(
        db_session,
        organization_id="00000000-0000-0000-0000-000000010901",
        driver_id="00000000-0000-0000-0000-000000010902",
        load_number="LD-DRIVER-DENY",
    )
    with pytest.raises(ForbiddenError):
        _authorize_submission_download(item=load, token_payload={"role": "driver"})
