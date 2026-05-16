from __future__ import annotations


def test_upload_response_returns_under_one_second_with_background_work_deferred(
    db_session,
    tmp_path,
    monkeypatch,
) -> None:
    import asyncio
    import time
    from io import BytesIO

    from app.api.v1.documents import upload_document
    from app.core.config import get_settings
    from app.domain.models.customer_account import CustomerAccount
    from app.domain.models.driver import Driver
    from app.domain.models.organization import Organization
    from app.services.loads.load_service import LoadService
    from fastapi import BackgroundTasks
    from starlette.datastructures import UploadFile

    org_id = "00000000-0000-0000-0000-000000078401"
    customer_id = "00000000-0000-0000-0000-000000078411"
    driver_id = "00000000-0000-0000-0000-000000078421"
    monkeypatch.setenv("STORAGE_LOCAL_ROOT", str(tmp_path))
    monkeypatch.setenv("DOCUMENT_UPLOAD_EXTRACTION_ENABLED", "true")
    get_settings.cache_clear()

    db_session.add(Organization(id=org_id, name="Upload Fast Org", slug="upload-fast-org"))
    db_session.add(
        CustomerAccount(
            id=customer_id,
            organization_id=org_id,
            account_name="Upload Fast Customer",
            account_code="UPF",
            status="active",
        )
    )
    db_session.add(
        Driver(
            id=driver_id,
            organization_id=org_id,
            customer_account_id=customer_id,
            full_name="Upload Fast Driver",
            phone="5557840",
            email=None,
            is_active=True,
        )
    )
    db_session.flush()
    load = LoadService(db_session).create_load(
        organization_id=org_id,
        customer_account_id=customer_id,
        driver_id=driver_id,
        load_number="UPF-001",
    )

    def slow_deferred_notification(**kwargs) -> None:
        time.sleep(1.25)

    monkeypatch.setattr(
        "app.api.v1.documents._create_document_uploaded_notification",
        slow_deferred_notification,
    )

    background_tasks = BackgroundTasks()
    started_at = time.perf_counter()
    response = asyncio.run(
        upload_document(
            organization_id=org_id,
            token_payload={
                "organization_id": org_id,
                "role": "owner",
                "sub": "00000000-0000-0000-0000-000000009998",
            },
            customer_account_id=customer_id,
            source_channel="manual",
            file=UploadFile(
                filename="proof_of_delivery.pdf",
                file=BytesIO(b"%PDF-1.4\nfast pod\n%%EOF"),
                headers={"content-type": "application/pdf"},
            ),
            driver_id=driver_id,
            load_id=str(load.id),
            document_type="proof_of_delivery",
            uploaded_by_staff_user_id=None,
            page_count=None,
            replace=None,
            db=db_session,
            background_tasks=background_tasks,
        )
    )
    elapsed = time.perf_counter() - started_at

    db_session.refresh(load)
    assert elapsed < 1
    assert response.meta["uploaded"] is True
    assert response.meta["document_processing"]["deferred"] is True
    assert response.meta["document_processing"]["extraction_status"] == "queued"
    for field in (
        "auth_ms",
        "multipart_parse_ms",
        "db_lookup_ms",
        "file_save_ms",
        "db_insert_ms",
        "readiness_recompute_ms",
        "background_task_ms",
        "commit_ms",
        "response_ms",
        "total_ms",
    ):
        assert field in response.meta["timings"]
    assert load.has_ratecon is False
    assert load.documents_complete is False
    assert len(background_tasks.tasks) == 1
    background_tasks.tasks.clear()
    monkeypatch.delenv("STORAGE_LOCAL_ROOT", raising=False)
    monkeypatch.delenv("DOCUMENT_UPLOAD_EXTRACTION_ENABLED", raising=False)
    get_settings.cache_clear()


