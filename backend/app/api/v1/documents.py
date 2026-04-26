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
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.core.exceptions import UnauthorizedError
from app.core.security import get_current_token_payload
from app.domain.enums.channel import Channel
from app.repositories.driver_repo import DriverRepository
from app.repositories.load_repo import LoadRepository
from app.schemas.common import ApiResponse
from app.services.ai.extraction_service import ExtractionService
from app.services.documents.document_linker import DocumentLinker
from app.services.documents.document_service import DocumentService
from app.services.notifications.notification_service import NotificationService
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
MAX_UPLOAD_FILE_SIZE_BYTES = 15 * 1024 * 1024

DEFAULT_LOAD_DOCUMENT_PAGE_SIZE = 100


class DocumentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: uuid.UUID
    customer_account_id: uuid.UUID
    storage_key: str
    source_channel: str
    driver_id: uuid.UUID | None = None
    load_id: uuid.UUID | None = None
    document_type: str | None = None
    original_filename: str | None = None
    mime_type: str | None = None
    file_size_bytes: int | None = None
    storage_bucket: str | None = None
    page_count: int | None = None
    uploaded_by_staff_user_id: uuid.UUID | None = None


class ExtractDocumentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    force: bool = False


class ReprocessDocumentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    force_reclassification: bool = False
    force_reextraction: bool = False


class LinkDocumentToLoadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    load_id: uuid.UUID


class DocumentUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_type: str


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


def _authorize_document_mutation(
    *,
    item: Any,
    token_payload: dict[str, Any],
) -> None:
    token_org_id = token_payload.get("organization_id")
    if str(getattr(item, "organization_id", "")) != str(token_org_id):
        raise UnauthorizedError("Document is not in authenticated organization")

    token_role = str(token_payload.get("role") or "").strip().lower()
    if token_role == "driver":
        token_driver_id = token_payload.get("driver_id")
        if not token_driver_id:
            raise UnauthorizedError("Driver token is missing driver_id")
        if str(getattr(item, "driver_id", "")) != str(token_driver_id):
            raise UnauthorizedError("Drivers may only mutate their own documents")


def _get_token_role(token_payload: dict[str, Any]) -> str:
    return str(token_payload.get("role") or "").strip().lower()


def _get_token_driver_id(token_payload: dict[str, Any]) -> str | None:
    token_driver_id = token_payload.get("driver_id")
    if token_driver_id is None:
        return None
    normalized = str(token_driver_id).strip()
    return normalized or None


def _ensure_staff_role(token_payload: dict[str, Any]) -> None:
    if _get_token_role(token_payload) == "driver":
        raise UnauthorizedError("Driver accounts cannot access this endpoint")


def _serialize_document(item: Any) -> dict[str, Any]:
    load = getattr(item, "load", None)
    driver = getattr(item, "driver", None)
    uploaded_by_staff_user = getattr(item, "uploaded_by_staff_user", None)
    validation_issues = getattr(item, "validation_issues", None)
    extracted_fields = getattr(item, "extracted_fields", None)

    return {
        "id": str(item.id),
        "organization_id": str(item.organization_id),
        "customer_account_id": str(item.customer_account_id),
        "driver_id": str(item.driver_id) if getattr(item, "driver_id", None) else None,
        "driver_name": getattr(driver, "full_name", None) if driver else None,
        "load_id": str(item.load_id) if getattr(item, "load_id", None) else None,
        "load_number": getattr(load, "load_number", None) if load else None,
        "source_channel": _enum_to_string(getattr(item, "source_channel", None)),
        "document_type": _enum_to_string(getattr(item, "document_type", None)),
        "original_filename": getattr(item, "original_filename", None),
        "mime_type": getattr(item, "mime_type", None),
        "file_size_bytes": getattr(item, "file_size_bytes", None),
        "storage_bucket": getattr(item, "storage_bucket", None),
        "storage_key": getattr(item, "storage_key", None),
        "processing_status": _enum_to_string(getattr(item, "processing_status", None)),
        "page_count": getattr(item, "page_count", None),
        "classification_confidence": getattr(item, "classification_confidence", None),
        "ocr_completed_at": _to_iso_or_none(getattr(item, "ocr_completed_at", None)),
        "received_at": _to_iso_or_none(getattr(item, "received_at", None)),
        "uploaded_by_staff_user_id": (
            str(getattr(item, "uploaded_by_staff_user_id", None))
            if getattr(item, "uploaded_by_staff_user_id", None)
            else None
        ),
        "uploaded_by_staff_user_name": (
            getattr(uploaded_by_staff_user, "full_name", None)
            if uploaded_by_staff_user
            else None
        ),
        "validation_issue_count": (
            len(validation_issues) if isinstance(validation_issues, list) else None
        ),
        "extracted_field_count": (
            len(extracted_fields) if isinstance(extracted_fields, list) else None
        ),
        "created_at": _to_iso_or_none(getattr(item, "created_at", None)),
        "updated_at": _to_iso_or_none(getattr(item, "updated_at", None)),
    }


def _validate_upload_size(file_size_bytes: int | None) -> None:
    if file_size_bytes is None:
        return
    if file_size_bytes > MAX_UPLOAD_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                "File is too large. Maximum upload size is "
                f"{MAX_UPLOAD_FILE_SIZE_BYTES // (1024 * 1024)}MB."
            ),
        )


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


def _create_document_uploaded_notification(
    *,
    db: Session,
    organization_id: str,
    customer_account_id: str,
    document_id: str,
    driver_id: str | None,
    load_id: str | None,
) -> None:
    try:
        notification_service = NotificationService(db)
        notification_service.create_notification(
            organization_id=organization_id,
            channel=Channel.MANUAL.value,
            direction="inbound",
            message_type="document_uploaded",
            customer_account_id=customer_account_id,
            driver_id=driver_id,
            load_id=load_id,
            subject="Driver document uploaded",
            body_text=f"Document {document_id} was uploaded.",
            status="queued",
        )
    except Exception:
        # Keep upload path resilient even if notification creation fails.
        return


@router.post("/documents/upload", response_model=ApiResponse)
async def upload_document(
    *,
    organization_id: uuid.UUID = Form(...),
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
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
    _ = uploaded_by_staff_user_id
    _validate_upload_file(file)
    _ensure_staff_role(token_payload)
    token_org_id = token_payload.get("organization_id")
    if str(organization_id) != str(token_org_id):
        raise UnauthorizedError("organization_id does not match authenticated organization")

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
        _validate_upload_size(file_size_bytes)
        storage_bucket = storage_result.get("bucket")

        service = DocumentService(db)
        token_role = _get_token_role(token_payload)
        token_subject = str(token_payload.get("sub") or "").strip()
        server_uploaded_by_staff_user_id: str | None = None
        if token_role != "driver" and token_subject:
            server_uploaded_by_staff_user_id = token_subject


        item = service.create_document(
            organization_id=str(organization_id),
            customer_account_id=str(customer_account_id),
            storage_key=str(storage_key).strip(),
            storage_bucket=(
                _normalize_optional_text(str(storage_bucket))
                if storage_bucket is not None
                else None
            ),
            source_channel=normalized_source_channel,
            driver_id=_uuid_to_str(driver_id),
            load_id=_uuid_to_str(load_id),
            document_type=normalized_document_type,
            original_filename=_normalize_optional_text(file.filename),
            mime_type=_normalize_optional_text(file.content_type),
            file_size_bytes=file_size_bytes,
            page_count=page_count,
            uploaded_by_staff_user_id=server_uploaded_by_staff_user_id,
        )
        _create_document_uploaded_notification(
            db=db,
            organization_id=str(organization_id),
            customer_account_id=str(customer_account_id),
            document_id=str(item.id),
            driver_id=_uuid_to_str(driver_id),
            load_id=_uuid_to_str(load_id),
        )
        db.commit()

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


@router.post("/driver/documents/upload", response_model=ApiResponse)
async def upload_driver_document(
    *,
    organization_id: uuid.UUID = Form(...),
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    file: UploadFile = File(...),
    document_type: str = Form(...),
    load_id: uuid.UUID | None = Form(None),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    _validate_upload_file(file)
    normalized_document_type = _normalize_required_text(document_type, "document_type")

    token_org_id = token_payload.get("organization_id")
    token_role = str(token_payload.get("role") or "").strip().lower()
    token_driver_id = token_payload.get("driver_id")

    if str(organization_id) != str(token_org_id):
        raise UnauthorizedError("organization_id does not match authenticated organization")
    if token_role != "driver":
        raise UnauthorizedError("Only driver accounts can use this endpoint")
    if not token_driver_id:
        raise UnauthorizedError("Driver token is missing driver_id")

    driver_repo = DriverRepository(db)
    load_repo = LoadRepository(db)
    driver = driver_repo.get_by_id(token_driver_id)
    if driver is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Driver profile not found.")
    if str(driver.organization_id) != str(organization_id):
        raise UnauthorizedError("Driver profile organization mismatch")

    resolved_load_id: str | None = None
    if load_id is not None:
        load = load_repo.get_by_id(load_id)
        if load is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Load not found.")
        if str(load.organization_id) != str(organization_id):
            raise UnauthorizedError("Load organization mismatch")
        if str(load.driver_id) != str(driver.id):
            raise UnauthorizedError("Drivers may only attach documents to their own loads")
        resolved_load_id = str(load.id)

    try:
        storage = StorageService()
        storage_result = await storage.save_file(file)
        storage_key = storage_result.get("storage_key")
        if not storage_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Storage service did not return a storage key.",
            )

        _validate_upload_size(storage_result.get("size"))

        service = DocumentService(db)
        item = service.create_document(
            organization_id=str(organization_id),
            customer_account_id=str(driver.customer_account_id),
            storage_key=str(storage_key).strip(),
            storage_bucket=_normalize_optional_text(
                str(storage_result.get("bucket"))
            )
            if storage_result.get("bucket") is not None
            else None,
            source_channel="driver_portal",
            driver_id=str(driver.id),
            load_id=resolved_load_id,
            document_type=normalized_document_type,
            original_filename=_normalize_optional_text(file.filename),
            mime_type=_normalize_optional_text(file.content_type),
            file_size_bytes=storage_result.get("size"),
            page_count=None,
            uploaded_by_staff_user_id=None,
        )
        _create_document_uploaded_notification(
            db=db,
            organization_id=str(organization_id),
            customer_account_id=str(driver.customer_account_id),
            document_id=str(item.id),
            driver_id=str(driver.id),
            load_id=resolved_load_id,
        )
        db.commit()

        return ApiResponse(
            data=_serialize_document(item),
            meta={"uploaded": True, "driver_upload": True},
            error=None,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload document: {exc}",
        ) from exc


@router.post("/documents", response_model=ApiResponse)
def create_document(
    payload: DocumentCreateRequest,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    _ensure_staff_role(token_payload)
    token_org_id = token_payload.get("organization_id")
    if str(payload.organization_id) != str(token_org_id):
        raise UnauthorizedError("organization_id does not match authenticated organization")

    normalized_storage_key = _normalize_required_text(payload.storage_key, "storage_key")
    normalized_source_channel = _normalize_required_text(
        payload.source_channel,
        "source_channel",
    )

    service = DocumentService(db)
    item = service.create_document(
        organization_id=str(payload.organization_id),
        customer_account_id=str(payload.customer_account_id),
        storage_key=normalized_storage_key,
        source_channel=normalized_source_channel,
        driver_id=_uuid_to_str(payload.driver_id),
        load_id=_uuid_to_str(payload.load_id),
        document_type=_normalize_optional_text(payload.document_type),
        original_filename=_normalize_optional_text(payload.original_filename),
        mime_type=_normalize_optional_text(payload.mime_type),
        file_size_bytes=payload.file_size_bytes,
        storage_bucket=_normalize_optional_text(payload.storage_bucket),
        page_count=payload.page_count,
        uploaded_by_staff_user_id=_uuid_to_str(payload.uploaded_by_staff_user_id),
    )

    db.commit()

    return ApiResponse(
        data=_serialize_document(item),
        meta={"created": True},
        error=None,
    )


@router.get("/documents", response_model=ApiResponse)
def list_documents(
    *,
    organization_id: uuid.UUID | None = None,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    customer_account_id: uuid.UUID | None = None,
    driver_id: uuid.UUID | None = None,
    load_id: uuid.UUID | None = None,
    document_type: str | None = None,
    processing_status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=500),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    token_org_id = token_payload.get("organization_id")
    token_role = _get_token_role(token_payload)
    token_driver_id = _get_token_driver_id(token_payload)
    effective_org_id = organization_id or uuid.UUID(str(token_org_id))
    if str(effective_org_id) != str(token_org_id):
        raise UnauthorizedError("organization_id does not match authenticated organization")
    effective_driver_id = driver_id
    if token_role == "driver":
        if not token_driver_id:
            raise UnauthorizedError("Driver token is missing driver_id")
        if driver_id is not None and str(driver_id) != token_driver_id:
            raise UnauthorizedError("Drivers may only list their own documents")
        effective_driver_id = uuid.UUID(token_driver_id)

    service = DocumentService(db)
    items, total_count = service.list_documents(
        organization_id=_uuid_to_str(effective_org_id),
        customer_account_id=_uuid_to_str(customer_account_id),
        driver_id=_uuid_to_str(effective_driver_id),
        load_id=_uuid_to_str(load_id),
        document_type=_normalize_optional_text(document_type),
        processing_status=_normalize_optional_text(processing_status),
        page=page,
        page_size=page_size,
    )

    return ApiResponse(
        data=[_serialize_document(item) for item in items],
        meta=_build_document_list_meta(
            total_count=total_count,
            page=page,
            page_size=page_size,
            load_id=_uuid_to_str(load_id),
        ),
        error=None,
    )


@router.get("/loads/{load_id}/documents", response_model=ApiResponse)
def get_documents_by_load(
    load_id: uuid.UUID,
    *,
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_LOAD_DOCUMENT_PAGE_SIZE, ge=1, le=500),
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    token_org_id = token_payload.get("organization_id")
    token_role = _get_token_role(token_payload)
    token_driver_id = _get_token_driver_id(token_payload)
    load_repo = LoadRepository(db)
    load = load_repo.get_by_id(load_id)
    if load is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Load not found.")
    if str(load.organization_id) != str(token_org_id):
        raise UnauthorizedError("Load is not in authenticated organization")
    if token_role == "driver":
        if not token_driver_id:
            raise UnauthorizedError("Driver token is missing driver_id")
        if str(load.driver_id) != token_driver_id:
            raise UnauthorizedError("Drivers may only view documents for their own loads")

    service = DocumentService(db)
    items, total_count = service.list_documents(
        organization_id=str(token_org_id),
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


@router.get("/documents/{document_id}/download")
def download_document(
    document_id: uuid.UUID,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
):
    service = DocumentService(db)
    item = service.get_document(str(document_id))
    token_org_id = token_payload.get("organization_id")
    if str(item.organization_id) != str(token_org_id):
        raise UnauthorizedError("Document is not in authenticated organization")
    _authorize_document_mutation(item=item, token_payload=token_payload)

    storage_key = getattr(item, "storage_key", None)
    if not storage_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document storage key is missing.",
        )

    storage = StorageService()
    return storage.get_file(storage_key)


@router.get("/documents/{document_id}", response_model=ApiResponse)
def get_document(
    document_id: uuid.UUID,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = DocumentService(db)
    item = service.get_document(str(document_id))
    token_org_id = token_payload.get("organization_id")
    if str(item.organization_id) != str(token_org_id):
        raise UnauthorizedError("Document is not in authenticated organization")
    _authorize_document_mutation(item=item, token_payload=token_payload)

    return ApiResponse(data=_serialize_document(item), meta={}, error=None)


@router.patch("/documents/{document_id}", response_model=ApiResponse)
def update_document(
    document_id: uuid.UUID,
    payload: DocumentUpdateRequest,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = DocumentService(db)
    item = service.get_document_in_organization(
        document_id=str(document_id),
        organization_id=str(token_payload.get("organization_id")),
    )
    _authorize_document_mutation(item=item, token_payload=token_payload)
    updated = service.update_document_type(
        document_id=str(document_id),
        document_type=_normalize_required_text(payload.document_type, "document_type"),
    )
    db.commit()
    return ApiResponse(data=_serialize_document(updated), meta={"updated": True}, error=None)


@router.delete("/documents/{document_id}", response_model=ApiResponse)
def delete_document(
    document_id: uuid.UUID,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = DocumentService(db)
    item = service.get_document_in_organization(
        document_id=str(document_id),
        organization_id=str(token_payload.get("organization_id")),
    )
    _authorize_document_mutation(item=item, token_payload=token_payload)
    service.delete_document(document_id=str(document_id))
    db.commit()
    return ApiResponse(data={"id": str(document_id), "deleted": True}, meta={}, error=None)


@router.post("/documents/{document_id}/extract", response_model=ApiResponse)
def extract_document(
    document_id: uuid.UUID,
    payload: ExtractDocumentRequest,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    document_service = DocumentService(db)
    document = document_service.get_document_in_organization(
        document_id=str(document_id),
        organization_id=str(token_payload.get("organization_id")),
    )
    _authorize_document_mutation(item=document, token_payload=token_payload)

    service = ExtractionService(db)
    result = service.extract_document(document_id=str(document_id), force=payload.force)
    db.commit()

    return ApiResponse(data=result, meta={}, error=None)


@router.post("/documents/{document_id}/reprocess", response_model=ApiResponse)
def reprocess_document(
    document_id: uuid.UUID,
    payload: ReprocessDocumentRequest,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    service = DocumentService(db)
    document = service.get_document_in_organization(
        document_id=str(document_id),
        organization_id=str(token_payload.get("organization_id")),
    )
    _authorize_document_mutation(item=document, token_payload=token_payload)
    result = service.reprocess_document(
        document_id=str(document_id),
        force_reclassification=payload.force_reclassification,
        force_reextraction=payload.force_reextraction,
    )
    db.commit()

    return ApiResponse(data=result, meta={}, error=None)


@router.post("/documents/{document_id}/link", response_model=ApiResponse)
def link_document_to_load(
    document_id: uuid.UUID,
    payload: LinkDocumentToLoadRequest,
    token_payload: dict[str, Any] = Depends(get_current_token_payload),
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    document_service = DocumentService(db)
    document = document_service.get_document_in_organization(
        document_id=str(document_id),
        organization_id=str(token_payload.get("organization_id")),
    )
    _authorize_document_mutation(item=document, token_payload=token_payload)

    load_repo = LoadRepository(db)
    load = load_repo.get_by_id(payload.load_id)
    if load is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Load not found.")
    if str(load.organization_id) != str(token_payload.get("organization_id")):
        raise UnauthorizedError("Load is not in authenticated organization")

    token_role = str(token_payload.get("role") or "").strip().lower()
    if token_role == "driver":
        token_driver_id = token_payload.get("driver_id")
        if not token_driver_id:
            raise UnauthorizedError("Driver token is missing driver_id")
        if str(load.driver_id) != str(token_driver_id):
            raise UnauthorizedError("Drivers may only link documents to their own loads")

    linker = DocumentLinker(db)
    result = linker.link_document_to_load(
        document_id=str(document_id),
        load_id=str(payload.load_id),
    )
    db.commit()

    return ApiResponse(data=result, meta={}, error=None)
