from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from app.api.v1.documents import delete_document
from app.core.middleware import RequestConcurrencyLimitMiddleware
from app.domain.enums.channel import Channel
from app.domain.enums.document_type import DocumentType
from app.domain.enums.processing_status import ProcessingStatus
from app.domain.models.customer_account import CustomerAccount
from app.domain.models.driver import Driver
from app.domain.models.load_document import LoadDocument
from app.domain.models.organization import Organization
from app.services.documents.document_service import DocumentService
from app.services.loads.load_service import LoadService
from fastapi import HTTPException
from starlette.requests import Request


def _request() -> Request:
    scope = {
        "type": "http",
        "method": "DELETE",
        "path": "/api/v1/documents/00000000-0000-0000-0000-000000000001",
        "headers": [],
    }
    request = Request(scope)
    request.state.request_id = "delete-trace-test"
    request.state.limiter_bucket = "document_writes"
    request.state.limiter_wait_ms = 0
    return request


def _seed_base(db_session):
    org_id = uuid.uuid4()
    customer_id = uuid.uuid4()
    driver_id = uuid.uuid4()
    db_session.add(Organization(id=org_id, name="Delete Org", slug="delete-org"))
    db_session.add(
        CustomerAccount(
            id=customer_id,
            organization_id=org_id,
            account_name="Delete Customer",
            account_code="DEL",
            status="active",
        )
    )
    db_session.add(
        Driver(
            id=driver_id,
            organization_id=org_id,
            customer_account_id=customer_id,
            full_name="Delete Driver",
            phone="5558800",
            is_active=True,
        )
    )
    db_session.flush()
    load = LoadService(db_session).create_load(
        organization_id=str(org_id),
        customer_account_id=str(customer_id),
        driver_id=str(driver_id),
        load_number="DEL-001",
    )
    return org_id, customer_id, driver_id, load


def _add_doc(db_session, org_id, customer_id, driver_id, load_id, document_type):
    document = LoadDocument(
        organization_id=org_id,
        customer_account_id=customer_id,
        driver_id=driver_id,
        load_id=load_id,
        source_channel=Channel.MANUAL,
        document_type=document_type,
        original_filename=f"{document_type.value}.pdf",
        mime_type="application/pdf",
        file_size_bytes=10,
        storage_key=f"tests/{uuid.uuid4()}.pdf",
        file_hash_sha256=uuid.uuid4().hex + uuid.uuid4().hex,
        processing_status=ProcessingStatus.COMPLETED,
        received_at=datetime.now(UTC),
    )
    db_session.add(document)
    db_session.flush()
    return document


def test_background_panel_limiter_saturation_does_not_classify_delete_as_background_read() -> None:
    middleware = RequestConcurrencyLimitMiddleware(app=None)  # type: ignore[arg-type]

    assert (
        middleware.BUCKET_CONFIG["background_panel_reads"]["capacity"]
        < middleware.BUCKET_CONFIG["document_writes"]["capacity"]
    )
    request = type(
        "R",
        (),
        {
            "method": "DELETE",
            "url": type(
                "U",
                (),
                {"path": "/api/v1/documents/00000000-0000-0000-0000-000000088099"},
            )(),
        },
    )()
    assert middleware._bucket_for_request(request) == "document_writes"


@pytest.mark.parametrize(
    "busy_path",
    [
        "/api/v1/loads/00000000-0000-0000-0000-000000088041/packet-audit",
        "/api/v1/loads/00000000-0000-0000-0000-000000088041/submission-packets",
    ],
)
def test_delete_document_uses_bucket_independent_of_busy_optional_panels(busy_path: str) -> None:
    middleware = RequestConcurrencyLimitMiddleware(app=None)  # type: ignore[arg-type]
    req_type = type("R", (), {})
    url_type = type("U", (), {})
    busy = req_type()
    busy.method = "GET"
    busy.url = url_type()
    busy.url.path = busy_path
    delete = req_type()
    delete.method = "DELETE"
    delete.url = url_type()
    delete.url.path = "/api/v1/documents/00000000-0000-0000-0000-000000088099"

    assert middleware._bucket_for_request(busy) == "background_panel_reads"
    assert middleware._bucket_for_request(delete) == "document_writes"


def test_invoice_document_delete_returns_controlled_409(db_session) -> None:
    org_id, customer_id, driver_id, load = _seed_base(db_session)
    document = _add_doc(db_session, org_id, customer_id, driver_id, load.id, DocumentType.INVOICE)

    with pytest.raises(HTTPException) as exc:
        delete_document(
            document_id=document.id,
            request=_request(),
            token_payload={"organization_id": str(org_id), "role": "owner", "sub": str(driver_id)},
            db=db_session,
        )

    assert exc.value.status_code == 409
    assert exc.value.detail["message"] == (
        "Invoice documents are managed from the invoice workflow. "
        "Use Regenerate Invoice to replace this file."
    )


def test_regular_document_delete_removes_row_and_updates_readiness(db_session) -> None:
    org_id, customer_id, driver_id, load = _seed_base(db_session)
    ratecon = _add_doc(
        db_session, org_id, customer_id, driver_id, load.id, DocumentType.RATE_CONFIRMATION
    )
    _add_doc(db_session, org_id, customer_id, driver_id, load.id, DocumentType.INVOICE)
    service = DocumentService(db_session)
    service._sync_load_document_flags(str(load.id))
    db_session.flush()
    assert load.has_ratecon is True

    response = delete_document(
        document_id=ratecon.id,
        request=_request(),
        token_payload={"organization_id": str(org_id), "role": "owner", "sub": str(driver_id)},
        db=db_session,
    )

    assert response.data == {"id": str(ratecon.id), "deleted": True}
    assert DocumentService(db_session).document_repo.get_by_id(ratecon.id) is None
    db_session.refresh(load)
    assert load.has_ratecon is False


def test_delete_document_returns_under_one_second_when_storage_delete_is_delayed(
    db_session, monkeypatch
) -> None:
    from fastapi import BackgroundTasks

    org_id, customer_id, driver_id, load = _seed_base(db_session)
    document = _add_doc(
        db_session, org_id, customer_id, driver_id, load.id, DocumentType.RATE_CONFIRMATION
    )
    db_session.commit()

    def slow_storage_delete(*, relative_path: str) -> bool:
        import time

        time.sleep(1.25)
        return True

    monkeypatch.setattr(
        "app.api.v1.documents.StorageService.delete",
        lambda self, *, relative_path: slow_storage_delete(relative_path=relative_path),
    )

    import time

    background_tasks = BackgroundTasks()
    started_at = time.perf_counter()
    response = delete_document(
        document_id=document.id,
        request=_request(),
        token_payload={"organization_id": str(org_id), "role": "owner", "sub": str(driver_id)},
        db=db_session,
        background_tasks=background_tasks,
    )
    elapsed = time.perf_counter() - started_at

    assert response.data == {"id": str(document.id), "deleted": True}
    assert elapsed < 1


def test_delete_document_trace_logs_required_timing_fields(db_session, caplog) -> None:
    org_id, customer_id, driver_id, load = _seed_base(db_session)
    document = _add_doc(
        db_session, org_id, customer_id, driver_id, load.id, DocumentType.RATE_CONFIRMATION
    )

    with caplog.at_level("INFO", logger="app.api.v1.documents"):
        delete_document(
            document_id=document.id,
            request=_request(),
            token_payload={"organization_id": str(org_id), "role": "owner", "sub": str(driver_id)},
            db=db_session,
        )

    completed = [
        record for record in caplog.records if record.message == "Document delete trace completed"
    ][-1]
    for field in (
        "request_start_ms",
        "auth_ms",
        "db_lookup_ms",
        "invoice_guard_ms",
        "readiness_precompute_ms",
        "storage_delete_ms",
        "db_delete_ms",
        "orm_flush_ms",
        "readiness_recompute_ms",
        "audit_log_ms",
        "commit_ms",
        "response_serialize_ms",
        "total_ms",
        "request_id",
        "document_id",
        "load_id",
        "org_id",
        "user_id",
        "storage_backend",
        "storage_path",
        "document_type",
        "invoice_generated",
        "generated_invoice",
        "blocking_stage",
        "partial_success_before_timeout",
        "disconnect_cancel_trace",
    ):
        assert hasattr(completed, field), field
    assert completed.blocking_stage == "completed_before_response"
    assert completed.partial_success_before_timeout is True
