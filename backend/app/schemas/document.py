from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums.channel import Channel
from app.domain.enums.document_type import DocumentType
from app.domain.enums.processing_status import ProcessingStatus


class ApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, Any] | None = None


class DocumentUploadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: str
    customer_account_id: str
    driver_id: str | None = None
    load_id: str | None = None
    document_type: DocumentType | None = None
    source_channel: Channel = Channel.MANUAL
    uploaded_by_staff_user_id: str | None = None
    page_count: int | None = Field(default=None, ge=0)


class DocumentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: str
    customer_account_id: str
    storage_key: str
    source_channel: Channel
    driver_id: str | None = None
    load_id: str | None = None
    document_type: DocumentType | None = None
    original_filename: str | None = None
    mime_type: str | None = None
    file_size_bytes: int | None = Field(default=None, ge=0)
    storage_bucket: str | None = None
    page_count: int | None = Field(default=None, ge=0)
    uploaded_by_staff_user_id: str | None = None


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    organization_id: str
    customer_account_id: str
    driver_id: str | None = None
    load_id: str | None = None
    source_channel: Channel
    document_type: DocumentType | None = None
    original_filename: str | None = None
    mime_type: str | None = None
    file_size_bytes: int | None = None
    storage_bucket: str | None = None
    storage_key: str
    file_hash_sha256: str | None = None
    page_count: int | None = None
    processing_status: ProcessingStatus
    classification_confidence: float | None = None
    ocr_completed_at: datetime | None = None
    received_at: datetime
    uploaded_by_staff_user_id: str | None = None
    created_at: datetime
    updated_at: datetime


class DocumentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    organization_id: str
    customer_account_id: str
    driver_id: str | None = None
    load_id: str | None = None
    source_channel: Channel | None = None
    document_type: DocumentType | None = None
    original_filename: str | None = None
    mime_type: str | None = None
    file_size_bytes: int | None = None
    page_count: int | None = None
    processing_status: ProcessingStatus
    classification_confidence: float | None = None
    received_at: datetime
    created_at: datetime
    updated_at: datetime


class DocumentDownloadMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    filename: str | None = None
    mime_type: str | None = None
    storage_key: str


class DocumentLinkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    load_id: str


class DocumentReprocessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    force_reclassification: bool = False
    force_reextraction: bool = False


class DocumentExtractRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    force: bool = False


class ExtractedFieldRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    document_id: str
    load_id: str | None = None
    field_name: str
    field_value_text: str | None = None
    field_value_number: Decimal | None = None
    field_value_date: datetime | None = None
    field_value_json: dict[str, Any] | list[Any] | None = None
    confidence_score: Decimal
    source_model: str | None = None
    source_engine: str | None = None
    is_human_corrected: bool
    corrected_by_staff_user_id: str | None = None
    corrected_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ExtractedFieldCorrectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field_value_text: str | None = None
    field_value_number: Decimal | None = None
    field_value_date: datetime | None = None
    field_value_json: dict[str, Any] | list[Any] | None = None
    correction_reason: str | None = Field(default=None, max_length=1000)


class DocumentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: DocumentRead
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ApiError | None = None


class DocumentListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: list[DocumentListItem]
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ApiError | None = None


class DocumentUploadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: DocumentRead
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ApiError | None = None


class DocumentLinkResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: dict[str, Any]
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ApiError | None = None


class DocumentExtractResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: dict[str, Any]
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ApiError | None = None


class DocumentReprocessResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: dict[str, Any]
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ApiError | None = None


class ExtractedFieldListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: list[ExtractedFieldRead]
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ApiError | None = None


class ExtractedFieldResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: ExtractedFieldRead
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ApiError | None = None