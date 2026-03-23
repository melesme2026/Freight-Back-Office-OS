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