from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import ValidationError
from app.schemas.common import ApiResponse
from app.services.ai.extraction_service import ExtractionService
from app.services.documents.document_linker import DocumentLinker
from app.services.documents.document_service import DocumentService


router = APIRouter()


@router.post("/documents", response_model=ApiResponse)
def create_document(
    *,
    organization_id: str,
    customer_account_id: str,
    storage_key: str,
    source_channel: str,
    driver_id: str | None = None,
    load_id: str | None = None,
    document_type: str | None = None,
    original_filename: str | None = None,
    mime_type: str | None = None,
    file_size_bytes: int | None = None,
    storage_bucket: str | None = None,
    page_count: int | None = None,
    uploaded_by_staff_user_id: str | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        uuid.UUID(organization_id)
        uuid.UUID(customer_account_id)
        if driver_id:
            uuid.UUID(driver_id)
        if load_id:
            uuid.UUID(load_id)
        if uploaded_by_staff_user_id:
            uuid.UUID(uploaded_by_staff_user_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid UUID provided",
            details={
                "organization_id": organization_id,
                "customer_account_id": customer_account_id,
                "driver_id": driver_id,
                "load_id": load_id,
                "uploaded_by_staff_user_id": uploaded_by_staff_user_id,
            },
        ) from exc

    service = DocumentService(db)
    item = service.create_document(
        organization_id=organization_id,
        customer_account_id=customer_account_id,
        storage_key=storage_key,
        source_channel=source_channel,
        driver_id=driver_id,
        load_id=load_id,
        document_type=document_type,
        original_filename=original_filename,
        mime_type=mime_type,
        file_size_bytes=file_size_bytes,
        storage_bucket=storage_bucket,
        page_count=page_count,
        uploaded_by_staff_user_id=uploaded_by_staff_user_id,
    )

    return ApiResponse(
        data={
            "id": str(item.id),
            "organization_id": str(item.organization_id),
            "customer_account_id": str(item.customer_account_id),
            "driver_id": str(item.driver_id) if item.driver_id else None,
            "load_id": str(item.load_id) if item.load_id else None,
            "source_channel": str(item.source_channel),
            "document_type": str(item.document_type),
            "original_filename": item.original_filename,
            "mime_type": item.mime_type,
            "file_size_bytes": item.file_size_bytes,
            "storage_bucket": item.storage_bucket,
            "storage_key": item.storage_key,
            "file_hash_sha256": item.file_hash_sha256,
            "page_count": item.page_count,
            "processing_status": str(item.processing_status),
            "classification_confidence": item.classification_confidence,
            "ocr_completed_at": item.ocr_completed_at.isoformat() if item.ocr_completed_at else None,
            "received_at": item.received_at.isoformat(),
            "uploaded_by_staff_user_id": str(item.uploaded_by_staff_user_id) if item.uploaded_by_staff_user_id else None,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )


@router.get("/documents", response_model=ApiResponse)
def list_documents(
    *,
    organization_id: str | None = None,
    customer_account_id: str | None = None,
    driver_id: str | None = None,
    load_id: str | None = None,
    document_type: str | None = None,
    processing_status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        if organization_id:
            uuid.UUID(organization_id)
        if customer_account_id:
            uuid.UUID(customer_account_id)
        if driver_id:
            uuid.UUID(driver_id)
        if load_id:
            uuid.UUID(load_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid UUID provided",
            details={
                "organization_id": organization_id,
                "customer_account_id": customer_account_id,
                "driver_id": driver_id,
                "load_id": load_id,
            },
        ) from exc

    service = DocumentService(db)
    items, total = service.list_documents(
        organization_id=organization_id,
        customer_account_id=customer_account_id,
        driver_id=driver_id,
        load_id=load_id,
        document_type=document_type,
        processing_status=processing_status,
        page=page,
        page_size=page_size,
    )

    return ApiResponse(
        data=[
            {
                "id": str(item.id),
                "organization_id": str(item.organization_id),
                "customer_account_id": str(item.customer_account_id),
                "driver_id": str(item.driver_id) if item.driver_id else None,
                "load_id": str(item.load_id) if item.load_id else None,
                "source_channel": str(item.source_channel),
                "document_type": str(item.document_type),
                "original_filename": item.original_filename,
                "mime_type": item.mime_type,
                "file_size_bytes": item.file_size_bytes,
                "storage_bucket": item.storage_bucket,
                "storage_key": item.storage_key,
                "file_hash_sha256": item.file_hash_sha256,
                "page_count": item.page_count,
                "processing_status": str(item.processing_status),
                "classification_confidence": item.classification_confidence,
                "ocr_completed_at": item.ocr_completed_at.isoformat() if item.ocr_completed_at else None,
                "received_at": item.received_at.isoformat(),
                "uploaded_by_staff_user_id": str(item.uploaded_by_staff_user_id) if item.uploaded_by_staff_user_id else None,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat(),
            }
            for item in items
        ],
        meta={"page": page, "page_size": page_size, "total": total},
        error=None,
    )


@router.get("/documents/{document_id}", response_model=ApiResponse)
def get_document(
    document_id: str,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        uuid.UUID(document_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid document_id",
            details={"document_id": document_id},
        ) from exc

    service = DocumentService(db)
    item = service.get_document(document_id)

    return ApiResponse(
        data={
            "id": str(item.id),
            "organization_id": str(item.organization_id),
            "customer_account_id": str(item.customer_account_id),
            "driver_id": str(item.driver_id) if item.driver_id else None,
            "load_id": str(item.load_id) if item.load_id else None,
            "source_channel": str(item.source_channel),
            "document_type": str(item.document_type),
            "original_filename": item.original_filename,
            "mime_type": item.mime_type,
            "file_size_bytes": item.file_size_bytes,
            "storage_bucket": item.storage_bucket,
            "storage_key": item.storage_key,
            "file_hash_sha256": item.file_hash_sha256,
            "page_count": item.page_count,
            "processing_status": str(item.processing_status),
            "classification_confidence": item.classification_confidence,
            "ocr_completed_at": item.ocr_completed_at.isoformat() if item.ocr_completed_at else None,
            "received_at": item.received_at.isoformat(),
            "uploaded_by_staff_user_id": str(item.uploaded_by_staff_user_id) if item.uploaded_by_staff_user_id else None,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        },
        meta={},
        error=None,
    )


@router.post("/documents/{document_id}/extract", response_model=ApiResponse)
def extract_document(
    document_id: str,
    *,
    force: bool = False,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        uuid.UUID(document_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid document_id",
            details={"document_id": document_id},
        ) from exc

    service = ExtractionService(db)
    result = service.extract_document(document_id=document_id, force=force)

    return ApiResponse(data=result, meta={}, error=None)


@router.post("/documents/{document_id}/reprocess", response_model=ApiResponse)
def reprocess_document(
    document_id: str,
    *,
    force_reclassification: bool = False,
    force_reextraction: bool = False,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        uuid.UUID(document_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid document_id",
            details={"document_id": document_id},
        ) from exc

    service = DocumentService(db)
    result = service.reprocess_document(
        document_id=document_id,
        force_reclassification=force_reclassification,
        force_reextraction=force_reextraction,
    )

    return ApiResponse(data=result, meta={}, error=None)


@router.post("/documents/{document_id}/link", response_model=ApiResponse)
def link_document_to_load(
    document_id: str,
    *,
    load_id: str,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    try:
        uuid.UUID(document_id)
        uuid.UUID(load_id)
    except ValueError as exc:
        raise ValidationError(
            "Invalid UUID provided",
            details={"document_id": document_id, "load_id": load_id},
        ) from exc

    linker = DocumentLinker(db)
    result = linker.link_document_to_load(document_id=document_id, load_id=load_id)

    return ApiResponse(data=result, meta={}, error=None)