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
    assert str(fetched.processing_status) == "pending"


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

    for index, document_type in enumerate(["rate_confirmation", "proof_of_delivery", "invoice"], start=1):
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
