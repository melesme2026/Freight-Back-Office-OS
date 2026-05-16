from __future__ import annotations

from app.services.documents.document_service import DocumentService


def test_create_and_get_document(db_session) -> None:
    service = DocumentService(db_session)

    created = service.create_document(
        organization_id="00000000-0000-0000-0000-000000000401",
        customer_account_id="00000000-0000-0000-0000-000000000402",
        storage_key="uploads/test-document.pdf",
        source_channel="manual",
        original_filename="test-document.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        storage_bucket="local",
    )

    fetched = service.get_document(str(created.id))

    assert str(fetched.id) == str(created.id)
    assert fetched.storage_key == "uploads/test-document.pdf"
    assert fetched.original_filename == "test-document.pdf"
    assert str(fetched.processing_status) == "queued"


def test_list_documents_returns_created_document(db_session) -> None:
    service = DocumentService(db_session)

    service.create_document(
        organization_id="00000000-0000-0000-0000-000000000411",
        customer_account_id="00000000-0000-0000-0000-000000000412",
        storage_key="uploads/another-test-document.pdf",
        source_channel="manual",
        original_filename="another-test-document.pdf",
        mime_type="application/pdf",
        file_size_bytes=2048,
        storage_bucket="local",
    )

    items, total = service.list_documents(
        organization_id="00000000-0000-0000-0000-000000000411",
        page=1,
        page_size=25,
    )

    assert total >= 1
    assert any(item.original_filename == "another-test-document.pdf" for item in items)


def test_document_sync_marks_submission_ready_without_bol(db_session) -> None:
    from app.services.loads.load_service import LoadService

    load_service = LoadService(db_session)
    document_service = DocumentService(db_session)

    load = load_service.create_load(
        organization_id="00000000-0000-0000-0000-000000000421",
        customer_account_id="00000000-0000-0000-0000-000000000422",
        driver_id="00000000-0000-0000-0000-000000000423",
    )

    for index, document_type in enumerate(
        ["rate_confirmation", "proof_of_delivery", "invoice"], start=1
    ):
        document_service.create_document(
            organization_id="00000000-0000-0000-0000-000000000421",
            customer_account_id="00000000-0000-0000-0000-000000000422",
            storage_key=f"uploads/submission-ready-{index}.pdf",
            source_channel="manual",
            load_id=str(load.id),
            document_type=document_type,
            original_filename=f"submission-ready-{index}.pdf",
            mime_type="application/pdf",
            file_size_bytes=1024 + index,
        )

    refreshed = load_service.get_load(str(load.id))

    assert refreshed.has_ratecon is True
    assert refreshed.has_invoice is True
    assert refreshed.has_bol is False
    assert refreshed.documents_complete is True


def test_update_document_type_alias_and_delete_resync_flags(db_session) -> None:
    from app.services.loads.load_service import LoadService

    load_service = LoadService(db_session)
    document_service = DocumentService(db_session)

    load = load_service.create_load(
        organization_id="00000000-0000-0000-0000-000000000431",
        customer_account_id="00000000-0000-0000-0000-000000000432",
        driver_id="00000000-0000-0000-0000-000000000433",
    )

    document = document_service.create_document(
        organization_id="00000000-0000-0000-0000-000000000431",
        customer_account_id="00000000-0000-0000-0000-000000000432",
        storage_key="uploads/editable-doc.pdf",
        source_channel="manual",
        load_id=str(load.id),
        document_type="unknown",
        original_filename="editable-doc.pdf",
        mime_type="application/pdf",
        file_size_bytes=1234,
    )

    updated = document_service.update_document_type(
        document_id=str(document.id),
        document_type="bill of lading",
    )
    refreshed = load_service.get_load(str(load.id))

    assert str(updated.document_type) == "bill_of_lading"
    assert refreshed.has_bol is True

    document_service.delete_document(document_id=str(document.id))
    refreshed_after_delete = load_service.get_load(str(load.id))
    assert refreshed_after_delete.has_bol is False


def test_small_multipart_pdf_upload_then_document_list_refresh(
    db_session,
    tmp_path,
    monkeypatch,
) -> None:
    import asyncio
    from io import BytesIO

    from app.api.v1.documents import upload_document
    from app.core.config import get_settings
    from app.domain.enums.processing_status import ProcessingStatus
    from app.domain.models.customer_account import CustomerAccount
    from app.domain.models.driver import Driver
    from app.domain.models.organization import Organization
    from app.services.loads.load_service import LoadService
    from starlette.datastructures import UploadFile

    org_id = "00000000-0000-0000-0000-000000078001"
    customer_id = "00000000-0000-0000-0000-000000078011"
    driver_id = "00000000-0000-0000-0000-000000078021"
    monkeypatch.setenv("STORAGE_LOCAL_ROOT", str(tmp_path))
    monkeypatch.setenv("DOCUMENT_UPLOAD_EXTRACTION_ENABLED", "false")
    get_settings.cache_clear()

    db_session.add(
        Organization(id=org_id, name="Upload Refresh Org", slug="upload-refresh-org")
    )
    db_session.add(
        CustomerAccount(
            id=customer_id,
            organization_id=org_id,
            account_name="Upload Refresh Customer",
            account_code="UPR",
            status="active",
        )
    )
    db_session.add(
        Driver(
            id=driver_id,
            organization_id=org_id,
            customer_account_id=customer_id,
            full_name="Upload Refresh Driver",
            phone="5557800",
            email=None,
            is_active=True,
        )
    )
    db_session.flush()
    load_service = LoadService(db_session)
    load = load_service.create_load(
        organization_id=org_id,
        customer_account_id=customer_id,
        driver_id=driver_id,
        load_number="UPR-001",
    )

    upload_responses = []
    for doc_type, filename, body in (
        ("proof_of_delivery", "proof_of_delivery.pdf", b"%PDF-1.4\nsmall pod\n%%EOF"),
        ("rate_confirmation", "rate_confirmation.pdf", b"%PDF-1.4\nsmall rate con\n%%EOF"),
    ):
        upload_responses.append(
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
                        filename=filename,
                        file=BytesIO(body),
                        headers={"content-type": "application/pdf"},
                    ),
                    driver_id=driver_id,
                    load_id=str(load.id),
                    document_type=doc_type,
                    uploaded_by_staff_user_id=None,
                    page_count=None,
                    replace=None,
                    db=db_session,
                )
            )
        )

    response = upload_responses[0]
    items, total = DocumentService(db_session).list_documents(
        organization_id=org_id,
        load_id=str(load.id),
        page=1,
        page_size=25,
    )
    refreshed_load = load_service.get_load(str(load.id))

    assert response.meta["uploaded"] is True
    assert response.meta["document_processing"]["skipped"] is True
    assert (
        response.meta["document_processing"]["extraction_status"]
        == ProcessingStatus.SKIPPED.value
    )
    assert response.data["received_status"] == "received"
    assert response.data["extraction_status"] == ProcessingStatus.SKIPPED.value
    assert total == 2
    by_filename = {item.original_filename: item for item in items}
    assert by_filename["proof_of_delivery.pdf"].processing_status == ProcessingStatus.COMPLETED
    assert by_filename["rate_confirmation.pdf"].processing_status == ProcessingStatus.COMPLETED
    assert refreshed_load.documents_complete is False
    assert any(
        document.original_filename == "proof_of_delivery.pdf"
        for document in refreshed_load.documents
    )
    get_settings.cache_clear()


def test_pod_upload_mark_extraction_skipped_does_not_remain_pending(db_session) -> None:
    from app.domain.enums.processing_status import ProcessingStatus
    from app.services.loads.load_service import LoadService

    org_id = "00000000-0000-0000-0000-000000078101"
    customer_id = "00000000-0000-0000-0000-000000078111"
    driver_id = "00000000-0000-0000-0000-000000078121"
    load = LoadService(db_session).create_load(
        organization_id=org_id,
        customer_account_id=customer_id,
        driver_id=driver_id,
        load_number="POD-NOT-PENDING-001",
    )
    document_service = DocumentService(db_session)
    document = document_service.create_document(
        organization_id=org_id,
        customer_account_id=customer_id,
        driver_id=driver_id,
        load_id=str(load.id),
        document_type="proof_of_delivery",
        storage_key="uploads/pod-not-pending.pdf",
        source_channel="manual",
        original_filename="pod-not-pending.pdf",
        mime_type="application/pdf",
        file_size_bytes=1700,
    )

    completed = document_service.mark_extraction_skipped(document_id=str(document.id))
    refreshed_load = LoadService(db_session).get_load(str(load.id))

    assert completed.processing_status == ProcessingStatus.COMPLETED
    assert completed.ocr_completed_at is None
    assert refreshed_load.documents_complete is False
    assert any(
        str(item.document_type) == "proof_of_delivery"
        and item.processing_status == ProcessingStatus.COMPLETED
        for item in refreshed_load.documents
    )


def test_delete_document_blocks_generated_invoice_documents(db_session) -> None:
    import pytest
    from app.api.v1.documents import delete_document
    from app.services.loads.load_service import LoadService
    from fastapi import HTTPException

    org_id = "00000000-0000-0000-0000-000000078201"
    customer_id = "00000000-0000-0000-0000-000000078211"
    driver_id = "00000000-0000-0000-0000-000000078221"
    load = LoadService(db_session).create_load(
        organization_id=org_id,
        customer_account_id=customer_id,
        driver_id=driver_id,
        load_number="INV-DELETE-BLOCK-001",
    )
    document = DocumentService(db_session).create_document(
        organization_id=org_id,
        customer_account_id=customer_id,
        driver_id=driver_id,
        load_id=str(load.id),
        document_type="invoice",
        storage_key="uploads/generated-invoice-delete-block.pdf",
        source_channel="manual",
        original_filename="generated-invoice-delete-block.pdf",
        mime_type="application/pdf",
        file_size_bytes=2048,
    )

    with pytest.raises(HTTPException) as exc_info:
        delete_document(
            document_id=document.id,
            token_payload={"organization_id": org_id, "role": "owner", "sub": driver_id},
            db=db_session,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["code"] == "invoice_document_managed_by_invoice_workflow"
    assert exc_info.value.detail["message"] == (
        "Invoice documents are managed from the invoice workflow. "
        "Use Regenerate Invoice to replace this file."
    )
    assert DocumentService(db_session).get_document(str(document.id)).id == document.id


def test_lightweight_documents_infers_pdf_mime_when_browser_omits_type(db_session) -> None:
    from app.api.v1.documents import get_documents_by_load
    from app.services.loads.load_service import LoadService

    org_id = "00000000-0000-0000-0000-000000078301"
    customer_id = "00000000-0000-0000-0000-000000078311"
    driver_id = "00000000-0000-0000-0000-000000078321"
    load = LoadService(db_session).create_load(
        organization_id=org_id,
        customer_account_id=customer_id,
        driver_id=driver_id,
        load_number="MIME-INFER-001",
    )
    DocumentService(db_session).create_document(
        organization_id=org_id,
        customer_account_id=customer_id,
        driver_id=driver_id,
        load_id=str(load.id),
        document_type="proof_of_delivery",
        storage_key="uploads/no-content-type.pdf",
        source_channel="manual",
        original_filename="no-content-type.pdf",
        mime_type=None,
        file_size_bytes=4096,
    )

    response = get_documents_by_load(
        load_id=load.id,
        token_payload={"organization_id": org_id, "role": "owner", "sub": driver_id},
        page=1,
        page_size=100,
        db=db_session,
    )

    assert response.data[0]["mime_type"] == "application/pdf"
    assert response.data[0]["file_size_bytes"] == 4096
