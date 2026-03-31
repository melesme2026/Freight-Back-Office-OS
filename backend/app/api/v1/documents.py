from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.schemas.common import ApiResponse
from app.services.ai.extraction_service import ExtractionService
from app.services.documents.document_linker import DocumentLinker
from app.services.documents.document_service import DocumentService


router = APIRouter()


def _uuid_to_str(value: uuid.UUID | None) -> str | None:
    return str(value) if value is not None else None


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _to_iso_or_none(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return isoformat()
    return str(value)


def _serialize_document(item: Any) -> dict[str, Any]:
    return {
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
        "ocr_completed_at": _to_iso_or_none(item.ocr_completed_at),
        "received_at": _to_iso_or_none(item.received_at),
        "uploaded_by_staff_user_id": (
            str(item.uploaded_by_staff_user_id)
            if item.uploaded_by_staff_user_id
            else None
        ),
        "created_at": _to_iso_or_none(item.created_at),
        "updated_at": _to_iso_or_none(item.updated_at),
    }


@router.post("/documents", response_model=ApiResponse)
def create_document(
    *,
    organization_id: uuid.UUID,
    customer_account_id: uuid.UUID,
    storage_key: str,
    source_channel: str,
    driver_id: uuid.UUID | None = None,
    load_id: uuid.UUID | None = None,
    document_type: str | None = None,
    original_filename: str | None = None,
    mime_type: str | None = None,
    file_size_bytes: int | None = None,
    storage_bucket: str | None = None,
    page_count: int | None = None,
    uploaded_by_staff_user_id: uuid.UUID | None = None,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = DocumentService(db)
    item = service.create_document(
        organization_id=str(organization_id),
        customer_account_id=str(customer_account_id),
        storage_key=storage_key.strip(),
        source_channel=source_channel.strip(),
        driver_id=_uuid_to_str(driver_id),
        load_id=_uuid_to_str(load_id),
        document_type=_normalize_optional_text(document_type),
        original_filename=_normalize_optional_text(original_filename),
        mime_type=_normalize_optional_text(mime_type),
        file_size_bytes=file_size_bytes,
        storage_bucket=_normalize_optional_text(storage_bucket),
        page_count=page_count,
        uploaded_by_staff_user_id=_uuid_to_str(uploaded_by_staff_user_id),
    )

    return ApiResponse(
        data=_serialize_document(item),
        meta={},
        error=None,
    )


@router.get("/documents", response_model=ApiResponse)
def list_documents(
    *,
    organization_id: uuid.UUID | None = None,
    customer_account_id: uuid.UUID | None = None,
    driver_id: uuid.UUID | None = None,
    load_id: uuid.UUID | None = None,
    document_type: str | None = None,
    processing_status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = DocumentService(db)
    items, total = service.list_documents(
        organization_id=_uuid_to_str(organization_id),
        customer_account_id=_uuid_to_str(customer_account_id),
        driver_id=_uuid_to_str(driver_id),
        load_id=_uuid_to_str(load_id),
        document_type=_normalize_optional_text(document_type),
        processing_status=_normalize_optional_text(processing_status),
        page=page,
        page_size=page_size,
    )

    return ApiResponse(
        data=[_serialize_document(item) for item in items],
        meta={
            "page": page,
            "page_size": page_size,
            "total": total,
        },
        error=None,
    )


@router.get("/documents/{document_id}", response_model=ApiResponse)
def get_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = DocumentService(db)
    item = service.get_document(str(document_id))

    return ApiResponse(
        data=_serialize_document(item),
        meta={},
        error=None,
    )


@router.post("/documents/{document_id}/extract", response_model=ApiResponse)
def extract_document(
    document_id: uuid.UUID,
    *,
    force: bool = False,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = ExtractionService(db)
    result = service.extract_document(document_id=str(document_id), force=force)

    return ApiResponse(
        data=result,
        meta={},
        error=None,
    )


@router.post("/documents/{document_id}/reprocess", response_model=ApiResponse)
def reprocess_document(
    document_id: uuid.UUID,
    *,
    force_reclassification: bool = False,
    force_reextraction: bool = False,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = DocumentService(db)
    result = service.reprocess_document(
        document_id=str(document_id),
        force_reclassification=force_reclassification,
        force_reextraction=force_reextraction,
    )

    return ApiResponse(
        data=result,
        meta={},
        error=None,
    )


@router.post("/documents/{document_id}/link", response_model=ApiResponse)
def link_document_to_load(
    document_id: uuid.UUID,
    *,
    load_id: uuid.UUID,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    linker = DocumentLinker(db)
    result = linker.link_document_to_load(
        document_id=str(document_id),
        load_id=str(load_id),
    )

    return ApiResponse(
        data=result,
        meta={},
        error=None,
    )