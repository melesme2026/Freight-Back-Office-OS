from __future__ import annotations

import asyncio
from io import BytesIO

import pytest
from fastapi import HTTPException
from starlette.datastructures import UploadFile

from app.api.v1.documents import upload_document, upload_driver_document
from app.domain.models.customer_account import CustomerAccount
from app.domain.models.driver import Driver
from app.domain.models.organization import Organization
from app.services.documents.document_service import DocumentService
from app.services.loads.load_service import LoadService


def _seed_base(db_session):
    org_id = "00000000-0000-0000-0000-000000077001"
    customer_id = "00000000-0000-0000-0000-000000077011"
    driver_id = "00000000-0000-0000-0000-000000077021"
    db_session.add(Organization(id=org_id, name="Dup Org", slug="dup-org"))
    db_session.add(CustomerAccount(id=customer_id, organization_id=org_id, account_name="Dup Customer", account_code="DUP", status="active"))
    db_session.add(Driver(id=driver_id, organization_id=org_id, customer_account_id=customer_id, full_name="Dup Driver", phone="5557700", email=None, is_active=True))
    db_session.flush()
    load = LoadService(db_session).create_load(
        organization_id=org_id,
        customer_account_id=customer_id,
        driver_id=driver_id,
        load_number="DUP-001",
        pickup_location="A",
        delivery_location="B",
    )
    return org_id, customer_id, driver_id, str(load.id)


def test_owner_duplicate_required_doc_returns_409_contract(db_session):
    org_id, customer_id, driver_id, load_id = _seed_base(db_session)

    async def _upload(replace: str | None = None):
        return await upload_document(
            organization_id=org_id,
            token_payload={"organization_id": org_id, "role": "owner", "sub": "00000000-0000-0000-0000-000000009999"},
            customer_account_id=customer_id,
            source_channel="manual",
            file=UploadFile(filename="pod.pdf", file=BytesIO(b"pod-one"), headers={"content-type": "application/pdf"}),
            driver_id=driver_id,
            load_id=load_id,
            document_type="proof_of_delivery",
            uploaded_by_staff_user_id=None,
            page_count=None,
            replace=replace,
            db=db_session,
        )

    asyncio.run(_upload())
    with pytest.raises(HTTPException) as exc:
        asyncio.run(_upload())

    assert exc.value.status_code == 409
    detail = exc.value.detail
    assert detail["code"] == "duplicate_required_document"
    assert detail["existing_document_id"]
    assert detail["document_type"] == "proof_of_delivery"
    assert detail["can_replace"] is True


def test_owner_replace_keeps_single_required_document(db_session):
    org_id, customer_id, driver_id, load_id = _seed_base(db_session)

    asyncio.run(upload_document(
        organization_id=org_id,
        token_payload={"organization_id": org_id, "role": "owner", "sub": "00000000-0000-0000-0000-000000009999"},
        customer_account_id=customer_id,
        source_channel="manual",
        file=UploadFile(filename="pod.pdf", file=BytesIO(b"pod-one"), headers={"content-type": "application/pdf"}),
        driver_id=driver_id,
        load_id=load_id,
        document_type="proof_of_delivery",
        uploaded_by_staff_user_id=None,
        page_count=None,
        replace=None,
        db=db_session,
    ))
    asyncio.run(upload_document(
        organization_id=org_id,
        token_payload={"organization_id": org_id, "role": "owner", "sub": "00000000-0000-0000-0000-000000009999"},
        customer_account_id=customer_id,
        source_channel="manual",
        file=UploadFile(filename="pod-2.pdf", file=BytesIO(b"pod-two"), headers={"content-type": "application/pdf"}),
        driver_id=driver_id,
        load_id=load_id,
        document_type="proof_of_delivery",
        uploaded_by_staff_user_id=None,
        page_count=None,
        replace="true",
        db=db_session,
    ))

    docs, _ = DocumentService(db_session).list_documents(
        organization_id=org_id,
        load_id=load_id,
        document_type="proof_of_delivery",
        page=1,
        page_size=20,
    )
    assert len(docs) == 1


def test_driver_duplicate_and_replace_flow(db_session):
    org_id, _, driver_id, load_id = _seed_base(db_session)
    payload = {"organization_id": org_id, "role": "driver", "driver_id": driver_id, "sub": driver_id}

    asyncio.run(upload_driver_document(
        organization_id=org_id,
        token_payload=payload,
        file=UploadFile(filename="pod.pdf", file=BytesIO(b"pod-one"), headers={"content-type": "application/pdf"}),
        document_type="proof_of_delivery",
        load_id=load_id,
        replace=None,
        db=db_session,
    ))

    with pytest.raises(HTTPException) as exc:
        asyncio.run(upload_driver_document(
            organization_id=org_id,
            token_payload=payload,
            file=UploadFile(filename="pod.pdf", file=BytesIO(b"pod-two"), headers={"content-type": "application/pdf"}),
            document_type="proof_of_delivery",
            load_id=load_id,
            replace=None,
            db=db_session,
        ))
    assert exc.value.status_code == 409

    replaced = asyncio.run(upload_driver_document(
        organization_id=org_id,
        token_payload=payload,
        file=UploadFile(filename="pod3.pdf", file=BytesIO(b"pod-three"), headers={"content-type": "application/pdf"}),
        document_type="proof_of_delivery",
        load_id=load_id,
        replace="true",
        db=db_session,
    ))
    assert replaced.meta["driver_upload"] is True


def test_invalid_owner_document_type_returns_validation_error_without_saving(
    db_session,
    tmp_path,
    monkeypatch,
):
    from app.core.config import get_settings
    from app.core.exceptions import ValidationError

    org_id, customer_id, driver_id, load_id = _seed_base(db_session)
    monkeypatch.setenv("STORAGE_LOCAL_ROOT", str(tmp_path))
    get_settings.cache_clear()

    with pytest.raises(ValidationError):
        asyncio.run(
            upload_document(
                organization_id=org_id,
                token_payload={
                    "organization_id": org_id,
                    "role": "owner",
                    "sub": "00000000-0000-0000-0000-000000009999",
                },
                customer_account_id=customer_id,
                source_channel="manual",
                file=UploadFile(
                    filename="bad.pdf",
                    file=BytesIO(b"bad-doc-type"),
                    headers={"content-type": "application/pdf"},
                ),
                driver_id=driver_id,
                load_id=load_id,
                document_type="not-a-real-doc-type",
                uploaded_by_staff_user_id=None,
                page_count=None,
                replace=None,
                db=db_session,
            )
        )

    assert list(tmp_path.rglob("*")) == []
    get_settings.cache_clear()


def test_storage_rejects_oversized_file_before_writing(tmp_path, monkeypatch):
    from app.core.config import get_settings
    from app.core.exceptions import ValidationError
    from app.services.documents.storage_service import StorageService

    monkeypatch.setenv("STORAGE_LOCAL_ROOT", str(tmp_path))
    get_settings.cache_clear()

    storage = StorageService()
    with pytest.raises(ValidationError) as exc:
        asyncio.run(
            storage.save_file(
                UploadFile(
                    filename="too-large.pdf",
                    file=BytesIO(b"x" * 11),
                    headers={"content-type": "application/pdf"},
                ),
                max_size_bytes=10,
            )
        )

    assert exc.value.details["max_size_bytes"] == 10
    assert not any(path.is_file() for path in tmp_path.rglob("*"))
    get_settings.cache_clear()


def test_owner_upload_cleans_up_file_when_database_create_fails(
    db_session,
    tmp_path,
    monkeypatch,
):
    from app.core.config import get_settings

    org_id, customer_id, driver_id, load_id = _seed_base(db_session)
    monkeypatch.setenv("STORAGE_LOCAL_ROOT", str(tmp_path))
    get_settings.cache_clear()

    def fail_create_document(self, *args, **kwargs):
        raise RuntimeError("simulated database failure")

    monkeypatch.setattr(DocumentService, "create_document", fail_create_document)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            upload_document(
                organization_id=org_id,
                token_payload={
                    "organization_id": org_id,
                    "role": "owner",
                    "sub": "00000000-0000-0000-0000-000000009999",
                },
                customer_account_id=customer_id,
                source_channel="manual",
                file=UploadFile(
                    filename="db-fail.pdf",
                    file=BytesIO(b"stored-then-rollback"),
                    headers={"content-type": "application/pdf"},
                ),
                driver_id=driver_id,
                load_id=load_id,
                document_type="proof_of_delivery",
                uploaded_by_staff_user_id=None,
                page_count=None,
                replace=None,
                db=db_session,
            )
        )

    assert exc.value.status_code == 500
    assert not any(path.is_file() for path in tmp_path.rglob("*"))
    get_settings.cache_clear()
