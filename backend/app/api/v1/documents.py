from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.schemas.common import ApiResponse
from app.services.ai.extraction_service import ExtractionService
from app.services.documents.document_linker import DocumentLinker
from app.services.documents.document_service import DocumentService
from app.services.documents.storage_service import StorageService


router = APIRouter()

ALLOWED_UPLOAD_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
    "image/tiff",
}

DEFAULT_LOAD_DOCUMENT_PAGE_SIZE = 100


# ---------------------------
# HELPERS
# ---------------------------

def _uuid_to_str(value: uuid.UUID | None) -> str | None:
    return str(value) if value is not None else None


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    return normalized or None


def _normalize_required_text(value: str | None, field_name: str) -> str:
    normalized = _normalize_optional_text(value)
    if normalized is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} is required.",
        )
    return normalized


def _to_iso_or_none(value: object | None) -> str | None:
    if value is None:
        return None

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return isoformat()

    return str(value)


def _enum_to_string(value: object | None) -> str | None:
    if value is None:
        return None

    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value

    return str(value)


def _serialize_document(item: Any) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "organization_id": str(item.organization_id),
        "customer_account_id": str(item.customer_account_id),
        "driver_id": str(item.driver_id) if getattr(item, "driver_id", None) else None,
        "load_id": str(item.load_id) if getattr(item, "load_id", None) else None,
        "source_channel": _enum_to_string(getattr(item, "source_channel", None)),
        "document_type": _enum_to_string(getattr(item, "document_type", None)),
        "original_filename": getattr(item, "original_filename", None),
        "mime_type": getattr(item, "mime_type", None),
        "file_size_bytes": getattr(item, "file_size_bytes", None),
        "storage_bucket": getattr(item, "storage_bucket", None),
        "storage_key": getattr(item, "storage_key", None),
        "processing_status": _enum_to_string(getattr(item, "processing_status", None)),
        "page_count": getattr(item, "page_count", None),
        "created_at": _to_iso_or_none(getattr(item, "created_at", None)),
        "updated_at": _to_iso_or_none(getattr(item, "updated_at", None)),
    }


def _validate_upload_file(file: UploadFile) -> None:
    filename = _normalize_optional_text(file.filename)
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A file with a valid filename is required.",
        )

    content_type = _normalize_optional_text(file.content_type)
    if content_type and content_type.lower() not in ALLOWED_UPLOAD_MIME_TYPES:
        allowed_types = ", ".join(sorted(ALLOWED_UPLOAD_MIME_TYPES))
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                "Unsupported file type. "
                f"Allowed MIME types: {allowed_types}."
            ),
        )


def _build_document_list_meta(
    *,
    total_count: int,
    page: int,
    page_size: int,
    load_id: str | None = None,
) -> dict[str, Any]:
    return {
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "load_id": load_id,
    }


# ---------------------------
# FILE UPLOAD ENDPOINT
# ---------------------------

@router.post("/documents/upload", response_model=ApiResponse)
async def upload_document(
    *,
    organization_id: uuid.UUID = Form(...),
    customer_account_id: uuid.UUID = Form(...),
    source_channel: str = Form(...),
    file: UploadFile = File(...),
    driver_id: uuid.UUID | None = Form(None),
    load_id: uuid.UUID | None = Form(None),
    document_type: str | None = Form(None),
    uploaded_by_staff_user_id: uuid.UUID | None = Form(None),
    page_count: int | None = Form(None),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    _validate_upload_file(file)

    normalized_source_channel = _normalize_required_text(source_channel, "source_channel")
    normalized_document_type = _normalize_optional_text(document_type)

    try:
        storage = StorageService()
        storage_result = await storage.save_file(file)

        storage_key = storage_result.get("storage_key")
        if not storage_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Storage service did not return a storage key.",
            )

        file_size_bytes = storage_result.get("size")
        storage_bucket = storage_result.get("bucket")

        service = DocumentService(db)
        item = service.create_document(
            organization_id=str(organization_id),
            customer_account_id=str(customer_account_id),
            storage_key=str(storage_key).strip(),
            storage_bucket=_normalize_optional_text(str(storage_bucket)) if storage_bucket is not None else None,
            source_channel=normalized_source_channel,
            driver_id=_uuid_to_str(driver_id),
            load_id=_uuid_to_str(load_id),
            document_type=normalized_document_type,
            original_filename=_normalize_optional_text(file.filename),
            mime_type=_normalize_optional_text(file.content_type),
            file_size_bytes=file_size_bytes,
            page_count=page_count,
            uploaded_by_staff_user_id=_uuid_to_str(uploaded_by_staff_user_id),
        )

        return ApiResponse(
            data=_serialize_document(item),
            meta={"uploaded": True},
            error=None,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload document: {exc}",
        ) from exc


# ---------------------------
# EXISTING METADATA CREATE ENDPOINT
# ---------------------------

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
    normalized_storage_key = _normalize_required_text(storage_key, "storage_key")
    normalized_source_channel = _normalize_required_text(source_channel, "source_channel")

    service = DocumentService(db)
    item = service.create_document(
        organization_id=str(organization_id),
        customer_account_id=str(customer_account_id),
        storage_key=normalized_storage_key,
        source_channel=normalized_source_channel,
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
        meta={"created": True},
        error=None,
    )


# ---------------------------
# LOAD DOCUMENT LIST ENDPOINT
# ---------------------------

@router.get("/loads/{load_id}/documents", response_model=ApiResponse)
def get_documents_by_load(
    load_id: uuid.UUID,
    *,
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_LOAD_DOCUMENT_PAGE_SIZE, ge=1, le=500),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = DocumentService(db)
    items, total_count = service.list_documents(
        load_id=str(load_id),
        page=page,
        page_size=page_size,
    )

    return ApiResponse(
        data=[_serialize_document(item) for item in items],
        meta=_build_document_list_meta(
            total_count=total_count,
            page=page,
            page_size=page_size,
            load_id=str(load_id),
        ),
        error=None,
    )


# ---------------------------
# DOWNLOAD FILE
# ---------------------------

@router.get("/documents/{document_id}/download")
def download_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db_session),
):
    service = DocumentService(db)
    item = service.get_document(str(document_id))

    storage_key = getattr(item, "storage_key", None)
    if not storage_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document storage key is missing.",
        )

    storage = StorageService()
    return storage.get_file(storage_key)


# ---------------------------
# EXISTING ADVANCED FEATURES
# ---------------------------

@router.get("/documents/{document_id}", response_model=ApiResponse)
def get_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = DocumentService(db)
    item = service.get_document(str(document_id))

    return ApiResponse(data=_serialize_document(item), meta={}, error=None)


@router.post("/documents/{document_id}/extract", response_model=ApiResponse)
def extract_document(
    document_id: uuid.UUID,
    *,
    force: bool = False,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = ExtractionService(db)
    result = service.extract_document(document_id=str(document_id), force=force)

    return ApiResponse(data=result, meta={}, error=None)


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

    return ApiResponse(data=result, meta={}, error=None)


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

    return ApiResponse(data=result, meta={}, error=None)