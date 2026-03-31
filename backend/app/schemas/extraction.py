from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums.document_type import DocumentType


class ApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: dict[str, Any] | None = None


class ExtractedFieldPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field_name: str = Field(min_length=1, max_length=100)
    field_value_text: str | None = None
    field_value_number: Decimal | None = None
    field_value_date: date | None = None
    field_value_json: dict[str, Any] | list[Any] | None = None
    confidence_score: Decimal = Field(ge=Decimal("0"), le=Decimal("1"))
    source_model: str | None = Field(default=None, max_length=100)
    source_engine: str | None = Field(default=None, max_length=100)


class DocumentExtractionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    load_id: str | None = None
    document_type: DocumentType | None = None
    force: bool = False


class DocumentExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    load_id: str | None = None
    document_type: DocumentType
    classification_confidence: Decimal | None = None
    extracted_fields: list[ExtractedFieldPayload]
    extraction_confidence_avg: Decimal | None = None
    extracted_at: datetime


class DocumentExtractionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: DocumentExtractionResult
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ApiError | None = None