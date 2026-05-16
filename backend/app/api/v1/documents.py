from __future__ import annotations

import logging
import mimetypes
import time
import uuid
from datetime import date, datetime
from typing import Annotated, Any

from app.core.cache import operational_cache
from app.core.config import get_settings
from app.core.dependencies import get_db_session
from app.core.exceptions import AppError, UnauthorizedError
from app.core.security import get_current_token_payload
from app.domain.enums.document_type import DocumentType
from app.domain.enums.processing_status import ProcessingStatus
from app.repositories.driver_repo import DriverRepository
from app.repositories.load_repo import LoadRepository
from app.schemas.common import ApiResponse
from app.services.ai.extraction_service import ExtractionService
from app.services.audit.audit_service import AuditService
from app.services.background.document_processing import (
    enqueue_document_extraction,
    run_document_extraction_job,
)
from app.services.documents.document_linker import DocumentLinker
from app.services.documents.document_service import DocumentService
from app.services.documents.storage_service import StorageService
from app.services.notifications.operational_notification_service import (
    OperationalNotificationService,
)
from app.services.organizations.quota_service import OrganizationQuotaService
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY = Depends(get_current_token_payload)
GET_DB_SESSION_DEPENDENCY = Depends(get_db_session)


router = APIRouter()
logger = logging.getLogger(__name__)

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
MAX_UPLOAD_FILE_SIZE_BYTES = get_settings().max_upload_file_size_mb * 1024 * 1024

DEFAULT_LOAD_DOCUMENT_PAGE_SIZE = 100


REQUIRED_SINGLETON_DOCUMENT_TYPES = {
    DocumentType.RATE_CONFIRMATION,
    DocumentType.BILL_OF_LADING,
    DocumentType.PROOF_OF_DELIVERY,
    DocumentType.INVOICE,
}


def _parse_replace_flag(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value or "").strip().lower()
    return normalized in {"1", "true", "yes", "on"}


def _document_label(value: DocumentType) -> str:
    labels = {
        DocumentType.RATE_CONFIRMATION: "Rate Confirmation",
        DocumentType.BILL_OF_LADING: "Bill of Lading",
        DocumentType.PROOF_OF_DELIVERY: "Proof of Delivery",
        DocumentType.INVOICE: "Invoice",
    }
    return labels.get(value, value.value.replace("_", " ").title())



def _infer_mime_type(filename: str | None, content_type: str | None) -> str | None:
    normalized_content_type = _normalize_optional_text(content_type)
    if normalized_content_type:
        return normalized_content_type.lower()
    normalized_filename = _normalize_optional_text(filename)
    if not normalized_filename:
        return None
    guessed, _ = mimetypes.guess_type(normalized_filename)
    if guessed:
        return guessed.lower()
    suffix = normalized_filename.rsplit(".", 1)[-1].lower() if "." in normalized_filename else ""
    return {
        "pdf": "application/pdf",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
        "heic": "image/heic",
        "heif": "image/heif",
        "tif": "image/tiff",
        "tiff": "image/tiff",
    }.get(suffix)


def _is_invoice_document(item: Any) -> bool:
    return _enum_to_string(getattr(item, "document_type", None)) == DocumentType.INVOICE.value


def _upload_log_context(
    *,
    organization_id: object,
    customer_account_id: object | None = None,
    driver_id: object | None = None,
    load_id: object | None = None,
    document_type: str | None = None,
    filename: str | None = None,
    upload_request_id: str | None = None,
    stage: str | None = None,
    elapsed_ms: int | None = None,
    file_size_bytes: int | None = None,
    storage_key: str | None = None,
    document_id: object | None = None,
) -> dict[str, Any]:
    return {
        "upload_request_id": upload_request_id,
        "upload_stage": stage,
        "upload_elapsed_ms": elapsed_ms,
        "organization_id": str(organization_id),
        "customer_account_id": (
            str(customer_account_id) if customer_account_id is not None else None
        ),
        "driver_id": str(driver_id) if driver_id is not None else None,
        "load_id": str(load_id) if load_id is not None else None,
        "document_id": str(document_id) if document_id is not None else None,
        "document_type": document_type,
        "file_size_bytes": file_size_bytes,
        "storage_key": storage_key,
        # Python LogRecord reserves `filename`, so keep the requested field in a nested context.
        "document_upload": {"filename": filename},
        "upload_filename": filename,
    }


def _log_upload_stage(
    *,
    stage: str,
    started_at: float,
    organization_id: object,
    customer_account_id: object | None = None,
    driver_id: object | None = None,
    load_id: object | None = None,
    document_type: str | None = None,
    filename: str | None = None,
    upload_request_id: str | None = None,
    file_size_bytes: int | None = None,
    storage_key: str | None = None,
    document_id: object | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    context = _upload_log_context(
        organization_id=organization_id,
        customer_account_id=customer_account_id,
        driver_id=driver_id,
        load_id=load_id,
        document_type=document_type,
        filename=filename,
        upload_request_id=upload_request_id,
        stage=stage,
        elapsed_ms=int((time.perf_counter() - started_at) * 1000),
        file_size_bytes=file_size_bytes,
        storage_key=storage_key,
        document_id=document_id,
    )
    if extra:
        context.update(extra)
    logger.info("Document upload stage completed", extra=context)


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


def _document_processing_value(item: Any) -> str | None:
    return _enum_to_string(getattr(item, "processing_status", None))


def _document_received_status(item: Any) -> str:
    if getattr(item, "received_at", None) is not None or getattr(
        item, "storage_key", None
    ):
        return "received"
    return "missing"


def _document_extraction_status(item: Any) -> str:
    processing_status = _document_processing_value(item)
    extraction_pending_statuses = {
        ProcessingStatus.FAILED.value,
        ProcessingStatus.IN_PROGRESS.value,
        ProcessingStatus.PROCESSING.value,
        ProcessingStatus.QUEUED.value,
        ProcessingStatus.PENDING.value,
    }
    if processing_status in extraction_pending_statuses:
        return processing_status
    if processing_status == ProcessingStatus.COMPLETED.value:
        if getattr(item, "ocr_completed_at", None) is None:
            return ProcessingStatus.SKIPPED.value
        return ProcessingStatus.COMPLETED.value
    return ProcessingStatus.NOT_REQUIRED.value


def _serialize_document(item: Any) -> dict[str, Any]:
    loaded_values = getattr(item, "__dict__", {})
    load = loaded_values.get("load")
    driver = loaded_values.get("driver")
    uploaded_by_staff_user = loaded_values.get("uploaded_by_staff_user")
    validation_issues = loaded_values.get("validation_issues")
    extracted_fields = loaded_values.get("extracted_fields")

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
        "received_status": _document_received_status(item),
        "processing_status": _document_processing_value(item),
        "extraction_status": _document_extraction_status(item),
        "validation_status": (
            "needs_review"
            if getattr(item, "validation_issues", None)
            else "not_required"
        ),
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


def _serialize_lightweight_document(item: Any) -> dict[str, Any]:
    mime_type = _infer_mime_type(
        getattr(item, "original_filename", None), getattr(item, "mime_type", None)
    )
    document_type = _enum_to_string(getattr(item, "document_type", None))
    return {
        "id": str(item.id),
        "organization_id": str(item.organization_id),
        "customer_account_id": str(item.customer_account_id),
        "driver_id": str(item.driver_id) if getattr(item, "driver_id", None) else None,
        "load_id": str(item.load_id) if getattr(item, "load_id", None) else None,
        "filename": getattr(item, "original_filename", None),
        "original_filename": getattr(item, "original_filename", None),
        "type": document_type,
        "document_type": document_type,
        "mime_type": mime_type,
        "file_size_bytes": getattr(item, "file_size_bytes", None),
        "uploaded_at": _to_iso_or_none(getattr(item, "received_at", None)),
        "received_at": _to_iso_or_none(getattr(item, "received_at", None)),
        "created_at": _to_iso_or_none(getattr(item, "created_at", None)),
        "updated_at": _to_iso_or_none(getattr(item, "updated_at", None)),
        "received_status": _document_received_status(item),
        "status": _document_processing_value(item),
        "processing_status": _document_processing_value(item),
        "extraction_status": _document_extraction_status(item),
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

    content_type = _infer_mime_type(filename, file.content_type)
    if content_type and content_type.lower() not in ALLOWED_UPLOAD_MIME_TYPES:
        allowed_types = ", ".join(sorted(ALLOWED_UPLOAD_MIME_TYPES))
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(f"Unsupported file type. Allowed MIME types: {allowed_types}."),
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


def _log_document_event(
    *,
    db: Session,
    organization_id: object,
    document_id: object,
    action: str,
    token_payload: dict[str, Any],
    metadata: dict[str, Any] | None = None,
) -> None:
    actor_id = str(token_payload.get("sub") or "").strip() or None
    actor_type = "staff_user" if actor_id else "system"
    AuditService(db).log_event(
        organization_id=str(organization_id),
        entity_type="document",
        entity_id=str(document_id),
        action=action,
        actor_id=actor_id,
        actor_type=actor_type,
        metadata_json=metadata or {},
    )


def _create_document_uploaded_notification(
    *,
    db: Session,
    document: Any,
    driver: Any | None = None,
    driver_confirmation: bool = False,
) -> None:
    try:
        OperationalNotificationService(db).document_uploaded(
            document=document,
            driver=driver,
            driver_confirmation=driver_confirmation,
        )
    except Exception:
        logger.exception(
            "Document upload notification failed",
            extra={"document_id": str(getattr(document, "id", ""))},
        )
        # Keep upload path resilient even if notification creation fails.
        return


def _queue_document_processing(
    *,
    document: Any | None = None,
    document_id: str | None = None,
    organization_id: str | None = None,
    background_tasks: BackgroundTasks | None,
    force: bool = False,
    upload_request_id: str | None = None,
) -> dict[str, Any] | None:
    settings = get_settings()
    resolved_document_id = document_id or str(document.id)
    resolved_organization_id = organization_id or str(document.organization_id)
    if not settings.document_upload_extraction_enabled:
        logger.info(
            "Document upload extraction skipped",
            extra={
                "upload_request_id": upload_request_id,
                "upload_stage": "extraction_skipped",
                "document_id": resolved_document_id,
                "organization_id": resolved_organization_id,
                "reason": "document_upload_extraction_disabled",
            },
        )
        return None

    job = enqueue_document_extraction(
        document_id=resolved_document_id,
        organization_id=resolved_organization_id,
        force=force,
    )
    if background_tasks is not None:
        background_tasks.add_task(
            run_document_extraction_job,
            job_id=str(job["id"]),
            document_id=resolved_document_id,
            force=force,
        )
    else:
        logger.info(
            "Document extraction job queued without an in-request background runner",
            extra={
                "upload_request_id": upload_request_id,
                "upload_stage": "extraction_queued",
                "document_id": resolved_document_id,
                "organization_id": resolved_organization_id,
                "job_id": str(job["id"]),
                "background_runner": False,
            },
        )
    return job


@router.post("/documents/upload", response_model=ApiResponse)
async def upload_document(
    *,
    organization_id: Annotated[uuid.UUID, Form()],
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    customer_account_id: Annotated[uuid.UUID, Form()],
    source_channel: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    driver_id: Annotated[uuid.UUID | None, Form()] = None,
    load_id: Annotated[uuid.UUID | None, Form()] = None,
    document_type: Annotated[str | None, Form()] = None,
    uploaded_by_staff_user_id: Annotated[uuid.UUID | None, Form()] = None,
    page_count: Annotated[int | None, Form()] = None,
    replace: Annotated[str | None, Form()] = None,
    db: Session = GET_DB_SESSION_DEPENDENCY,
    background_tasks: BackgroundTasks = None,
) -> ApiResponse:
    _ = uploaded_by_staff_user_id
    upload_request_id = uuid.uuid4().hex
    upload_started_at = time.perf_counter()
    _log_upload_stage(
        stage="request_received",
        started_at=upload_started_at,
        organization_id=organization_id,
        customer_account_id=customer_account_id,
        driver_id=driver_id,
        load_id=load_id,
        document_type=document_type,
        filename=file.filename,
        upload_request_id=upload_request_id,
        extra={"content_type": file.content_type},
    )
    _validate_upload_file(file)
    _log_upload_stage(
        stage="file_metadata_parsed",
        started_at=upload_started_at,
        organization_id=organization_id,
        customer_account_id=customer_account_id,
        driver_id=driver_id,
        load_id=load_id,
        document_type=document_type,
        filename=file.filename,
        upload_request_id=upload_request_id,
        extra={"content_type": file.content_type},
    )
    _ensure_staff_role(token_payload)
    token_org_id = token_payload.get("organization_id")
    if str(organization_id) != str(token_org_id):
        raise UnauthorizedError(
            "organization_id does not match authenticated organization"
        )
    _log_upload_stage(
        stage="auth_resolved",
        started_at=upload_started_at,
        organization_id=organization_id,
        customer_account_id=customer_account_id,
        driver_id=driver_id,
        load_id=load_id,
        document_type=document_type,
        filename=file.filename,
        upload_request_id=upload_request_id,
        extra={"token_role": _get_token_role(token_payload)},
    )

    normalized_source_channel = _normalize_required_text(
        source_channel, "source_channel"
    )
    normalized_document_type = _normalize_optional_text(document_type)
    storage: StorageService | None = None
    uploaded_storage_key: str | None = None

    try:
        service = DocumentService(db)
        token_role = _get_token_role(token_payload)
        token_subject = str(token_payload.get("sub") or "").strip()
        server_uploaded_by_staff_user_id: str | None = None
        if token_role != "driver" and token_subject:
            server_uploaded_by_staff_user_id = token_subject

        replace_existing = _parse_replace_flag(replace)
        parsed_document_type = service._normalize_document_type(
            normalized_document_type, allow_none=True
        )
        existing_required_doc = None
        if (
            parsed_document_type in REQUIRED_SINGLETON_DOCUMENT_TYPES
            and load_id is not None
        ):
            existing_required_doc = (
                service.document_repo.find_required_document_for_load(
                    organization_id=str(organization_id),
                    load_id=str(load_id),
                    document_type=parsed_document_type,
                )
            )

            if existing_required_doc and not replace_existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "duplicate_required_document",
                        "message": (
                            f"{_document_label(parsed_document_type)} already exists "
                            "for this load. "
                            "Replace it?"
                        ),
                        "existing_document_id": str(existing_required_doc.id),
                        "document_type": parsed_document_type.value,
                        "can_replace": True,
                    },
                )

        _log_upload_stage(
            stage="org_load_resolved",
            started_at=upload_started_at,
            organization_id=organization_id,
            customer_account_id=customer_account_id,
            driver_id=driver_id,
            load_id=load_id,
            document_type=normalized_document_type,
            filename=file.filename,
            upload_request_id=upload_request_id,
            extra={
                "replace_existing": replace_existing,
                "existing_document_id": (
                    str(existing_required_doc.id) if existing_required_doc else None
                ),
            },
        )

        storage = StorageService()
        storage_result = await storage.save_file(
            file, max_size_bytes=MAX_UPLOAD_FILE_SIZE_BYTES
        )

        storage_key = storage_result.get("storage_key")
        if not storage_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Storage service did not return a storage key.",
            )

        file_size_bytes = storage_result.get("size")
        _validate_upload_size(file_size_bytes)
        quota_decision = OrganizationQuotaService(db).can_upload_document(
            organization_id=str(organization_id),
            incoming_size_bytes=int(file_size_bytes or 0),
            enforce=False,
        )
        storage_bucket = storage_result.get("bucket")
        uploaded_storage_key = str(storage_key).strip()
        _log_upload_stage(
            stage="file_saved",
            started_at=upload_started_at,
            organization_id=organization_id,
            customer_account_id=customer_account_id,
            driver_id=driver_id,
            load_id=load_id,
            document_type=normalized_document_type,
            filename=file.filename,
            upload_request_id=upload_request_id,
            file_size_bytes=int(file_size_bytes or 0),
            storage_key=uploaded_storage_key,
            extra={"storage_bucket": storage_bucket},
        )

        if existing_required_doc and replace_existing:
            old_storage_key = existing_required_doc.storage_key
            existing_required_doc.original_filename = _normalize_optional_text(
                file.filename
            )
            existing_required_doc.storage_key = str(storage_key).strip()
            existing_required_doc.storage_bucket = (
                _normalize_optional_text(str(storage_bucket))
                if storage_bucket is not None
                else None
            )
            existing_required_doc.mime_type = _infer_mime_type(file.filename, file.content_type)
            existing_required_doc.file_size_bytes = file_size_bytes
            existing_required_doc.processing_status = ProcessingStatus.QUEUED
            existing_required_doc.received_at = datetime.utcnow()
            existing_required_doc.ocr_completed_at = None
            if server_uploaded_by_staff_user_id:
                existing_required_doc.uploaded_by_staff_user_id = (
                    server_uploaded_by_staff_user_id
                )
            if not get_settings().document_upload_extraction_enabled:
                existing_required_doc.processing_status = ProcessingStatus.COMPLETED
            item = service.document_repo.update(existing_required_doc)
            if old_storage_key and old_storage_key != existing_required_doc.storage_key:
                storage.delete(relative_path=old_storage_key)
        else:
            item = service.create_document(
                organization_id=str(organization_id),
                customer_account_id=str(customer_account_id),
                storage_key=uploaded_storage_key,
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
                mime_type=_infer_mime_type(file.filename, file.content_type),
                file_size_bytes=file_size_bytes,
                page_count=page_count,
                uploaded_by_staff_user_id=server_uploaded_by_staff_user_id,
            )
            if not get_settings().document_upload_extraction_enabled:
                item = service.mark_extraction_skipped(document_id=str(item.id))
        _log_upload_stage(
            stage="db_document_row_created",
            started_at=upload_started_at,
            organization_id=organization_id,
            customer_account_id=customer_account_id,
            driver_id=driver_id,
            load_id=load_id,
            document_type=normalized_document_type,
            filename=file.filename,
            upload_request_id=upload_request_id,
            file_size_bytes=int(file_size_bytes or 0),
            storage_key=uploaded_storage_key,
            document_id=item.id,
            extra={"processing_status": _enum_to_string(item.processing_status)},
        )
        _create_document_uploaded_notification(db=db, document=item)
        _log_document_event(
            db=db,
            organization_id=organization_id,
            document_id=item.id,
            action=(
                "document.replaced"
                if existing_required_doc and replace_existing
                else "document.uploaded"
            ),
            token_payload=token_payload,
            metadata={
                "document_type": normalized_document_type,
                "filename": file.filename,
                "file_size_bytes": file_size_bytes,
                "load_id": str(load_id) if load_id else None,
                "warning": quota_decision.reason if quota_decision.warning else None,
            },
        )
        item_id = str(item.id)
        item_organization_id = str(item.organization_id)
        serialized_item = _serialize_lightweight_document(item)
        db.commit()
        _log_upload_stage(
            stage="db_transaction_committed",
            started_at=upload_started_at,
            organization_id=organization_id,
            customer_account_id=customer_account_id,
            driver_id=driver_id,
            load_id=load_id,
            document_type=normalized_document_type,
            filename=file.filename,
            upload_request_id=upload_request_id,
            file_size_bytes=int(file_size_bytes or 0),
            storage_key=uploaded_storage_key,
            document_id=item_id,
        )
        operational_cache.invalidate_namespace(
            "command_center", organization_id=str(organization_id)
        )
        operational_cache.invalidate_namespace(
            "operational_analytics", organization_id=str(organization_id)
        )
        processing_job = _queue_document_processing(
            document_id=item_id,
            organization_id=item_organization_id,
            background_tasks=background_tasks,
            upload_request_id=upload_request_id,
        )
        processing_meta = (
            {
                "status": ProcessingStatus.QUEUED.value,
                "extraction_status": ProcessingStatus.QUEUED.value,
                "job_id": processing_job["id"],
                "job_type": processing_job["job_type"],
                "idempotency_key": processing_job["idempotency_key"],
            }
            if processing_job is not None
            else {
                "status": ProcessingStatus.COMPLETED.value,
                "extraction_status": ProcessingStatus.SKIPPED.value,
                "job_id": None,
                "job_type": "document_extraction",
                "idempotency_key": None,
                "skipped": True,
                "reason": "document_upload_extraction_disabled",
            }
        )
        _log_upload_stage(
            stage=(
                "extraction_analysis_started"
                if processing_job
                else "extraction_analysis_skipped"
            ),
            started_at=upload_started_at,
            organization_id=organization_id,
            customer_account_id=customer_account_id,
            driver_id=driver_id,
            load_id=load_id,
            document_type=normalized_document_type,
            filename=file.filename,
            upload_request_id=upload_request_id,
            file_size_bytes=int(file_size_bytes or 0),
            storage_key=uploaded_storage_key,
            document_id=item_id,
            extra=processing_meta,
        )
        _log_upload_stage(
            stage="response_returned",
            started_at=upload_started_at,
            organization_id=organization_id,
            customer_account_id=customer_account_id,
            driver_id=driver_id,
            load_id=load_id,
            document_type=normalized_document_type,
            filename=file.filename,
            upload_request_id=upload_request_id,
            file_size_bytes=int(file_size_bytes or 0),
            storage_key=uploaded_storage_key,
            document_id=item_id,
        )

        return ApiResponse(
            data=serialized_item,
            meta={
                "uploaded": True,
                "quota": quota_decision.as_dict(),
                "document_processing": processing_meta,
            },
            error=None,
        )
    except HTTPException:
        if storage is not None and uploaded_storage_key:
            storage.delete(relative_path=uploaded_storage_key)
        raise
    except AppError as exc:
        db.rollback()
        if storage is not None and uploaded_storage_key:
            storage.delete(relative_path=uploaded_storage_key)
        logger.warning(
            "Known document upload failure",
            extra={
                **_upload_log_context(
                    organization_id=organization_id,
                    customer_account_id=customer_account_id,
                    driver_id=driver_id,
                    load_id=load_id,
                    document_type=normalized_document_type,
                    filename=file.filename,
                ),
                "error_code": exc.code,
            },
        )
        raise
    except Exception as exc:
        db.rollback()
        if storage is not None and uploaded_storage_key:
            storage.delete(relative_path=uploaded_storage_key)
        logger.exception(
            "Document upload failed",
            extra=_upload_log_context(
                organization_id=organization_id,
                customer_account_id=customer_account_id,
                driver_id=driver_id,
                load_id=load_id,
                document_type=normalized_document_type,
                filename=file.filename,
            ),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "document_upload_failed",
                "message": (
                    "Document upload failed. Please try again or contact support if it continues."
                ),
            },
        ) from exc
    finally:
        try:
            await file.close()
        except Exception:
            logger.warning(
                "Document upload file close failed",
                extra=_upload_log_context(
                    organization_id=organization_id,
                    customer_account_id=customer_account_id,
                    driver_id=driver_id,
                    load_id=load_id,
                    document_type=(
                        normalized_document_type
                        if "normalized_document_type" in locals()
                        else document_type
                    ),
                    filename=file.filename,
                    upload_request_id=upload_request_id,
                    stage="file_close_failed",
                    elapsed_ms=int((time.perf_counter() - upload_started_at) * 1000),
                ),
            )


@router.post("/driver/documents/upload", response_model=ApiResponse)
async def upload_driver_document(
    *,
    organization_id: Annotated[uuid.UUID, Form()],
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    file: Annotated[UploadFile, File()],
    document_type: Annotated[str, Form()],
    load_id: Annotated[uuid.UUID | None, Form()] = None,
    replace: Annotated[str | None, Form()] = None,
    db: Session = GET_DB_SESSION_DEPENDENCY,
    background_tasks: BackgroundTasks = None,
) -> ApiResponse:
    upload_request_id = uuid.uuid4().hex
    upload_started_at = time.perf_counter()
    _validate_upload_file(file)
    normalized_document_type = _normalize_required_text(document_type, "document_type")

    token_org_id = token_payload.get("organization_id")
    token_role = str(token_payload.get("role") or "").strip().lower()
    token_driver_id = token_payload.get("driver_id")

    if str(organization_id) != str(token_org_id):
        raise UnauthorizedError(
            "organization_id does not match authenticated organization"
        )
    if token_role != "driver":
        raise UnauthorizedError("Only driver accounts can use this endpoint")
    if not token_driver_id:
        raise UnauthorizedError("Driver token is missing driver_id")

    driver_repo = DriverRepository(db)
    load_repo = LoadRepository(db)
    driver = driver_repo.get_by_id(token_driver_id)
    if driver is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Driver profile not found."
        )
    if str(driver.organization_id) != str(organization_id):
        raise UnauthorizedError("Driver profile organization mismatch")

    resolved_load_id: str | None = None
    if load_id is not None:
        load = load_repo.get_by_id(load_id)
        if load is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Load not found."
            )
        if str(load.organization_id) != str(organization_id):
            raise UnauthorizedError("Load organization mismatch")
        if str(load.driver_id) != str(driver.id):
            raise UnauthorizedError(
                "Drivers may only attach documents to their own loads"
            )
        resolved_load_id = str(load.id)

    storage: StorageService | None = None
    uploaded_storage_key: str | None = None

    try:
        service = DocumentService(db)
        replace_existing = _parse_replace_flag(replace)
        parsed_document_type = service._normalize_document_type(
            normalized_document_type
        )
        existing_required_doc = None
        if (
            parsed_document_type in REQUIRED_SINGLETON_DOCUMENT_TYPES
            and resolved_load_id
        ):
            existing_required_doc = (
                service.document_repo.find_required_document_for_load(
                    organization_id=str(organization_id),
                    load_id=resolved_load_id,
                    document_type=parsed_document_type,
                )
            )
            if existing_required_doc and not replace_existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "duplicate_required_document",
                        "message": (
                            f"{_document_label(parsed_document_type)} already exists "
                            "for this load. "
                            "Replace it?"
                        ),
                        "existing_document_id": str(existing_required_doc.id),
                        "document_type": parsed_document_type.value,
                        "can_replace": True,
                    },
                )

        _log_upload_stage(
            stage="org_load_resolved",
            started_at=upload_started_at,
            organization_id=organization_id,
            customer_account_id=getattr(driver, "customer_account_id", None),
            driver_id=token_driver_id,
            load_id=load_id,
            document_type=normalized_document_type,
            filename=file.filename,
            upload_request_id=upload_request_id,
            extra={
                "replace_existing": replace_existing,
                "existing_document_id": (
                    str(existing_required_doc.id) if existing_required_doc else None
                ),
            },
        )

        storage = StorageService()
        storage_result = await storage.save_file(
            file, max_size_bytes=MAX_UPLOAD_FILE_SIZE_BYTES
        )
        storage_key = storage_result.get("storage_key")
        if not storage_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Storage service did not return a storage key.",
            )

        file_size_bytes = storage_result.get("size")
        _validate_upload_size(file_size_bytes)
        quota_decision = OrganizationQuotaService(db).can_upload_document(
            organization_id=str(organization_id),
            incoming_size_bytes=int(file_size_bytes or 0),
            enforce=False,
        )
        uploaded_storage_key = str(storage_key).strip()

        if existing_required_doc and replace_existing:
            old_storage_key = existing_required_doc.storage_key
            existing_required_doc.original_filename = _normalize_optional_text(
                file.filename
            )
            existing_required_doc.storage_key = str(storage_key).strip()
            existing_required_doc.storage_bucket = (
                _normalize_optional_text(str(storage_result.get("bucket")))
                if storage_result.get("bucket") is not None
                else None
            )
            existing_required_doc.mime_type = _infer_mime_type(file.filename, file.content_type)
            existing_required_doc.file_size_bytes = file_size_bytes
            existing_required_doc.processing_status = (
                ProcessingStatus.QUEUED
                if get_settings().document_upload_extraction_enabled
                else ProcessingStatus.COMPLETED
            )
            existing_required_doc.ocr_completed_at = None
            existing_required_doc.received_at = datetime.utcnow()
            item = service.document_repo.update(existing_required_doc)
            if old_storage_key and old_storage_key != existing_required_doc.storage_key:
                storage.delete(relative_path=old_storage_key)
        else:
            item = service.create_document(
                organization_id=str(organization_id),
                customer_account_id=str(driver.customer_account_id),
                storage_key=uploaded_storage_key,
                storage_bucket=(
                    _normalize_optional_text(str(storage_result.get("bucket")))
                    if storage_result.get("bucket") is not None
                    else None
                ),
                source_channel="driver_portal",
                driver_id=str(driver.id),
                load_id=resolved_load_id,
                document_type=normalized_document_type,
                original_filename=_normalize_optional_text(file.filename),
                mime_type=_infer_mime_type(file.filename, file.content_type),
                file_size_bytes=file_size_bytes,
                page_count=None,
                uploaded_by_staff_user_id=None,
            )
            if not get_settings().document_upload_extraction_enabled:
                item = service.mark_extraction_skipped(document_id=str(item.id))
        _create_document_uploaded_notification(
            db=db,
            document=item,
            driver=driver,
            driver_confirmation=True,
        )
        _log_document_event(
            db=db,
            organization_id=organization_id,
            document_id=item.id,
            action=(
                "document.replaced"
                if existing_required_doc and replace_existing
                else "document.uploaded"
            ),
            token_payload=token_payload,
            metadata={
                "document_type": normalized_document_type,
                "filename": file.filename,
                "file_size_bytes": file_size_bytes,
                "load_id": str(load_id) if load_id else None,
                "warning": quota_decision.reason if quota_decision.warning else None,
            },
        )
        item_id = str(item.id)
        item_organization_id = str(item.organization_id)
        serialized_item = _serialize_lightweight_document(item)
        db.commit()
        _log_upload_stage(
            stage="db_transaction_committed",
            started_at=upload_started_at,
            organization_id=organization_id,
            customer_account_id=getattr(driver, "customer_account_id", None),
            driver_id=token_driver_id,
            load_id=load_id,
            document_type=normalized_document_type,
            filename=file.filename,
            upload_request_id=upload_request_id,
            file_size_bytes=int(file_size_bytes or 0),
            storage_key=uploaded_storage_key,
            document_id=item_id,
        )
        operational_cache.invalidate_namespace(
            "command_center", organization_id=str(organization_id)
        )
        operational_cache.invalidate_namespace(
            "operational_analytics", organization_id=str(organization_id)
        )
        processing_job = _queue_document_processing(
            document_id=item_id,
            organization_id=item_organization_id,
            background_tasks=background_tasks,
            upload_request_id=upload_request_id,
        )
        processing_meta = (
            {
                "status": ProcessingStatus.QUEUED.value,
                "extraction_status": ProcessingStatus.QUEUED.value,
                "job_id": processing_job["id"],
                "job_type": processing_job["job_type"],
                "idempotency_key": processing_job["idempotency_key"],
            }
            if processing_job is not None
            else {
                "status": ProcessingStatus.COMPLETED.value,
                "extraction_status": ProcessingStatus.SKIPPED.value,
                "job_id": None,
                "job_type": "document_extraction",
                "idempotency_key": None,
                "skipped": True,
                "reason": "document_upload_extraction_disabled",
            }
        )
        _log_upload_stage(
            stage=(
                "extraction_analysis_started"
                if processing_job
                else "extraction_analysis_skipped"
            ),
            started_at=upload_started_at,
            organization_id=organization_id,
            customer_account_id=getattr(driver, "customer_account_id", None),
            driver_id=token_driver_id,
            load_id=load_id,
            document_type=normalized_document_type,
            filename=file.filename,
            upload_request_id=upload_request_id,
            file_size_bytes=int(file_size_bytes or 0),
            storage_key=uploaded_storage_key,
            document_id=item_id,
            extra=processing_meta,
        )
        _log_upload_stage(
            stage="response_returned",
            started_at=upload_started_at,
            organization_id=organization_id,
            customer_account_id=getattr(driver, "customer_account_id", None),
            driver_id=token_driver_id,
            load_id=load_id,
            document_type=normalized_document_type,
            filename=file.filename,
            upload_request_id=upload_request_id,
            file_size_bytes=int(file_size_bytes or 0),
            storage_key=uploaded_storage_key,
            document_id=item_id,
        )

        return ApiResponse(
            data=serialized_item,
            meta={
                "uploaded": True,
                "driver_upload": True,
                "quota": quota_decision.as_dict(),
                "document_processing": processing_meta,
            },
            error=None,
        )
    except HTTPException:
        if storage is not None and uploaded_storage_key:
            storage.delete(relative_path=uploaded_storage_key)
        raise
    except AppError as exc:
        db.rollback()
        if storage is not None and uploaded_storage_key:
            storage.delete(relative_path=uploaded_storage_key)
        logger.warning(
            "Known driver document upload failure",
            extra={
                **_upload_log_context(
                    organization_id=organization_id,
                    customer_account_id=getattr(driver, "customer_account_id", None),
                    driver_id=token_driver_id,
                    load_id=load_id,
                    document_type=normalized_document_type,
                    filename=file.filename,
                ),
                "error_code": exc.code,
            },
        )
        raise
    except Exception as exc:
        db.rollback()
        if storage is not None and uploaded_storage_key:
            storage.delete(relative_path=uploaded_storage_key)
        logger.exception(
            "Driver document upload failed",
            extra=_upload_log_context(
                organization_id=organization_id,
                customer_account_id=getattr(driver, "customer_account_id", None),
                driver_id=token_driver_id,
                load_id=load_id,
                document_type=normalized_document_type,
                filename=file.filename,
            ),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "document_upload_failed",
                "message": (
                    "Document upload failed. Please try again or contact support if it continues."
                ),
            },
        ) from exc


@router.post("/documents", response_model=ApiResponse)
def create_document(
    payload: DocumentCreateRequest,
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = GET_DB_SESSION_DEPENDENCY,
) -> ApiResponse:
    _ensure_staff_role(token_payload)
    token_org_id = token_payload.get("organization_id")
    if str(payload.organization_id) != str(token_org_id):
        raise UnauthorizedError(
            "organization_id does not match authenticated organization"
        )

    normalized_storage_key = _normalize_required_text(
        payload.storage_key, "storage_key"
    )
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

    _log_document_event(
        db=db,
        organization_id=payload.organization_id,
        document_id=item.id,
        action="document.created",
        token_payload=token_payload,
        metadata={
            "document_type": payload.document_type,
            "filename": payload.original_filename,
        },
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
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    customer_account_id: uuid.UUID | None = None,
    driver_id: uuid.UUID | None = None,
    load_id: uuid.UUID | None = None,
    document_type: str | None = None,
    processing_status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=500),
    db: Session = GET_DB_SESSION_DEPENDENCY,
) -> ApiResponse:
    token_org_id = token_payload.get("organization_id")
    token_role = _get_token_role(token_payload)
    token_driver_id = _get_token_driver_id(token_payload)
    effective_org_id = organization_id or uuid.UUID(str(token_org_id))
    if str(effective_org_id) != str(token_org_id):
        raise UnauthorizedError(
            "organization_id does not match authenticated organization"
        )
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
        include_related=True,
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
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = GET_DB_SESSION_DEPENDENCY,
) -> ApiResponse:
    token_org_id = token_payload.get("organization_id")
    token_role = _get_token_role(token_payload)
    token_driver_id = _get_token_driver_id(token_payload)
    load_repo = LoadRepository(db)
    load = load_repo.get_by_id(load_id)
    if load is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Load not found."
        )
    if str(load.organization_id) != str(token_org_id):
        raise UnauthorizedError("Load is not in authenticated organization")
    if token_role == "driver":
        if not token_driver_id:
            raise UnauthorizedError("Driver token is missing driver_id")
        if str(load.driver_id) != token_driver_id:
            raise UnauthorizedError(
                "Drivers may only view documents for their own loads"
            )

    service = DocumentService(db)
    started_at = time.perf_counter()
    items, total_count = service.list_documents(
        organization_id=str(token_org_id),
        load_id=str(load_id),
        page=page,
        page_size=page_size,
        include_related=False,
    )
    elapsed_ms = int((time.perf_counter() - started_at) * 1000)
    logger.info(
        "Lightweight load documents endpoint completed",
        extra={
            "load_id": str(load_id),
            "organization_id": str(token_org_id),
            "document_count": len(items),
            "elapsed_ms": elapsed_ms,
            "hydration_mode": "lightweight",
        },
    )

    return ApiResponse(
        data=[_serialize_lightweight_document(item) for item in items],
        meta=_build_document_list_meta(
            total_count=total_count,
            page=page,
            page_size=page_size,
            load_id=str(load_id),
        )
        | {"elapsed_ms": elapsed_ms, "hydration_mode": "lightweight"},
        error=None,
    )


@router.get("/documents/{document_id}/download")
def download_document(
    document_id: uuid.UUID,
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = GET_DB_SESSION_DEPENDENCY,
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
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = GET_DB_SESSION_DEPENDENCY,
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
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = GET_DB_SESSION_DEPENDENCY,
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
    _log_document_event(
        db=db,
        organization_id=updated.organization_id,
        document_id=updated.id,
        action="document.updated",
        token_payload=token_payload,
        metadata={"document_type": payload.document_type},
    )
    db.commit()
    return ApiResponse(
        data=_serialize_document(updated), meta={"updated": True}, error=None
    )


@router.delete("/documents/{document_id}", response_model=ApiResponse)
def delete_document(
    document_id: uuid.UUID,
    request: Request,
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = GET_DB_SESSION_DEPENDENCY,
) -> ApiResponse:
    trace_started_at = time.perf_counter()
    timings: dict[str, int] = {
        "db_lookup_ms": 0,
        "invoice_doc_guard_ms": 0,
        "file_storage_delete_ms": 0,
        "db_delete_ms": 0,
        "commit_ms": 0,
    }
    trace_context: dict[str, Any] = {
        "request_id": getattr(request.state, "request_id", None),
        "document_id": str(document_id),
        "load_id": None,
        "org_id": (
            str(token_payload.get("organization_id"))
            if token_payload.get("organization_id")
            else None
        ),
        "user_id": str(token_payload.get("sub")) if token_payload.get("sub") else None,
        "limiter_bucket": getattr(request.state, "limiter_bucket", None),
        "limiter_wait_ms": getattr(request.state, "limiter_wait_ms", None),
        "client_disconnected": None,
    }

    try:
        service = DocumentService(db)
        stage_started_at = time.perf_counter()
        item = service.get_document_in_organization(
            document_id=str(document_id),
            organization_id=str(token_payload.get("organization_id")),
        )
        timings["db_lookup_ms"] = int((time.perf_counter() - stage_started_at) * 1000)
        trace_context.update(
            {
                "load_id": str(item.load_id) if getattr(item, "load_id", None) else None,
                "org_id": str(item.organization_id),
                "document_type": _enum_to_string(item.document_type),
                "processing_status": _document_processing_value(item),
            }
        )
        _authorize_document_mutation(item=item, token_payload=token_payload)

        stage_started_at = time.perf_counter()
        if _is_invoice_document(item):
            timings["invoice_doc_guard_ms"] = int((time.perf_counter() - stage_started_at) * 1000)
            logger.info(
                "Document delete trace completed",
                extra={
                    **trace_context,
                    **timings,
                    "response_ms": int((time.perf_counter() - trace_started_at) * 1000),
                    "delete_outcome": "invoice_document_guard_rejected",
                    "status_code": status.HTTP_409_CONFLICT,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "invoice_document_managed_by_invoice_workflow",
                    "message": (
                        "Invoice documents are managed from the invoice workflow. "
                        "Use Regenerate Invoice to replace this file."
                    ),
                },
            )
        timings["invoice_doc_guard_ms"] = int((time.perf_counter() - stage_started_at) * 1000)

        storage_key = getattr(item, "storage_key", None)
        if storage_key:
            stage_started_at = time.perf_counter()
            try:
                StorageService().delete(relative_path=storage_key)
            except Exception:
                logger.exception(
                    "Document storage delete failed during document delete",
                    extra={**trace_context, "storage_key": storage_key},
                )
            timings["file_storage_delete_ms"] = int((time.perf_counter() - stage_started_at) * 1000)

        _log_document_event(
            db=db,
            organization_id=item.organization_id,
            document_id=item.id,
            action="document.deleted",
            token_payload=token_payload,
            metadata={
                "document_type": _enum_to_string(item.document_type),
                "filename": item.original_filename,
            },
        )

        load_id = str(item.load_id) if item.load_id else None
        stage_started_at = time.perf_counter()
        service.document_repo.delete(item)
        db.expire_all()
        if load_id:
            service._sync_load_document_flags(load_id)
        timings["db_delete_ms"] = int((time.perf_counter() - stage_started_at) * 1000)

        stage_started_at = time.perf_counter()
        db.commit()
        timings["commit_ms"] = int((time.perf_counter() - stage_started_at) * 1000)

        logger.info(
            "Document delete trace completed",
            extra={
                **trace_context,
                **timings,
                "response_ms": int((time.perf_counter() - trace_started_at) * 1000),
                "delete_outcome": "deleted",
                "status_code": status.HTTP_200_OK,
            },
        )
        return ApiResponse(
            data={"id": str(document_id), "deleted": True}, meta={}, error=None
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "Document delete trace failed",
            extra={
                **trace_context,
                **timings,
                "response_ms": int((time.perf_counter() - trace_started_at) * 1000),
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
            },
        )
        raise


@router.post("/documents/{document_id}/extract", response_model=ApiResponse)
def extract_document(
    document_id: uuid.UUID,
    payload: ExtractDocumentRequest,
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = GET_DB_SESSION_DEPENDENCY,
) -> ApiResponse:
    document_service = DocumentService(db)
    document = document_service.get_document_in_organization(
        document_id=str(document_id),
        organization_id=str(token_payload.get("organization_id")),
    )
    _authorize_document_mutation(item=document, token_payload=token_payload)

    document_service.mark_processing(
        document_id=str(document_id),
        processing_status=ProcessingStatus.IN_PROGRESS,
    )
    service = ExtractionService(db)
    try:
        result = service.extract_document(
            document_id=str(document_id), force=payload.force
        )
    except Exception:
        document_service.mark_processing(
            document_id=str(document_id),
            processing_status=ProcessingStatus.FAILED,
        )
        db.commit()
        raise
    db.commit()

    return ApiResponse(data=result, meta={}, error=None)


@router.post("/documents/{document_id}/reprocess", response_model=ApiResponse)
def reprocess_document(
    document_id: uuid.UUID,
    payload: ReprocessDocumentRequest,
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = GET_DB_SESSION_DEPENDENCY,
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
    token_payload: dict[str, Any] = GET_CURRENT_TOKEN_PAYLOAD_DEPENDENCY,
    db: Session = GET_DB_SESSION_DEPENDENCY,
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Load not found."
        )
    if str(load.organization_id) != str(token_payload.get("organization_id")):
        raise UnauthorizedError("Load is not in authenticated organization")

    token_role = str(token_payload.get("role") or "").strip().lower()
    if token_role == "driver":
        token_driver_id = token_payload.get("driver_id")
        if not token_driver_id:
            raise UnauthorizedError("Driver token is missing driver_id")
        if str(load.driver_id) != str(token_driver_id):
            raise UnauthorizedError(
                "Drivers may only link documents to their own loads"
            )

    linker = DocumentLinker(db)
    result = linker.link_document_to_load(
        document_id=str(document_id),
        load_id=str(payload.load_id),
    )
    db.commit()

    return ApiResponse(data=result, meta={}, error=None)
