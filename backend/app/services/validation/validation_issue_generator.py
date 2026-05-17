from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.domain.enums.document_type import DocumentType, normalize_document_type_value
from app.domain.enums.validation_severity import ValidationSeverity
from app.domain.models.validation_issue import ValidationIssue
from sqlalchemy import select
from sqlalchemy.orm import Session

LOW_CONFIDENCE_THRESHOLD = 0.75
SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
    "image/tiff",
}


@dataclass(frozen=True)
class GeneratedValidationIssue:
    rule_code: str
    severity: ValidationSeverity
    title: str
    description: str
    is_blocking: bool
    remediation: str

    def model_kwargs(self) -> dict[str, Any]:
        return {
            "rule_code": self.rule_code,
            "severity": self.severity,
            "title": self.title,
            "description": f"{self.description} Remediation: {self.remediation}",
            "is_blocking": self.is_blocking,
        }


class ValidationIssueGenerator:
    """Canonical deterministic generator for operational review issues."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def generate(
        self,
        *,
        organization_id: str,
        load_id: str,
        document_id: str | None,
        payload: dict[str, Any],
    ) -> list[ValidationIssue]:
        generated = self.evaluate(payload=payload)
        if not generated:
            return []

        existing_codes = set(
            self.db.scalars(
                select(ValidationIssue.rule_code).where(
                    ValidationIssue.organization_id == organization_id,
                    ValidationIssue.load_id == load_id,
                    ValidationIssue.document_id == document_id,
                    ValidationIssue.is_resolved.is_(False),
                    ValidationIssue.rule_code.in_(
                        [item.rule_code for item in generated]
                    ),
                )
            ).all()
        )

        now = datetime.now(timezone.utc)
        issues: list[ValidationIssue] = []
        for item in generated:
            if item.rule_code in existing_codes:
                continue
            issues.append(
                ValidationIssue(
                    organization_id=organization_id,
                    load_id=load_id,
                    document_id=document_id,
                    created_at=now,
                    updated_at=now,
                    is_resolved=False,
                    resolved_by_staff_user_id=None,
                    resolved_at=None,
                    resolution_notes=None,
                    **item.model_kwargs(),
                )
            )

        if issues:
            self.db.add_all(issues)
            self.db.flush()
        return issues

    def evaluate(self, *, payload: dict[str, Any]) -> list[GeneratedValidationIssue]:
        issues: list[GeneratedValidationIssue] = []
        claimed = normalize_document_type_value(
            payload.get("claimed_document_type") or payload.get("document_type"),
            allow_none=True,
        )
        detected = normalize_document_type_value(
            payload.get("detected_document_type")
            or payload.get("classified_document_type"),
            allow_none=True,
        )

        raw_document_type = str(payload.get("document_type") or "").strip()
        if raw_document_type and claimed is None:
            issues.append(
                GeneratedValidationIssue(
                    rule_code="invalid_document_type_mapping",
                    severity=ValidationSeverity.ERROR,
                    title="Invalid document type mapping",
                    description=(
                        "The uploaded document type could not be mapped to a "
                        "supported operational type."
                    ),
                    is_blocking=True,
                    remediation=(
                        "Choose Proof of Delivery, Bill of Lading, Rate Confirmation, "
                        "Invoice, or Supporting Document and reprocess the file."
                    ),
                )
            )

        if (
            claimed
            and detected
            and claimed != detected
            and detected != DocumentType.UNKNOWN
        ):
            issues.append(
                GeneratedValidationIssue(
                    rule_code="wrong_document_classification",
                    severity=ValidationSeverity.ERROR,
                    title="Document classification mismatch",
                    description=(
                        f"The upload was labeled {claimed.value}, but extraction "
                        f"classified it as {detected.value}."
                    ),
                    is_blocking=True,
                    remediation=(
                        "Keep the existing approved document, relabel this upload as "
                        "supporting evidence, or explicitly replace after staff review."
                    ),
                )
            )

        mime_type = (
            str(payload.get("mime_type") or payload.get("content_type") or "")
            .lower()
            .strip()
        )
        supported = set(payload.get("supported_mime_types") or SUPPORTED_MIME_TYPES)
        if mime_type and mime_type not in supported:
            issues.append(
                GeneratedValidationIssue(
                    rule_code="unsupported_document_format",
                    severity=ValidationSeverity.ERROR,
                    title="Unsupported document format",
                    description=(
                        f"The uploaded file format {mime_type} is not supported "
                        "for document extraction."
                    ),
                    is_blocking=True,
                    remediation=(
                        "Upload a PDF or supported image file so dispatch and billing "
                        "can validate it safely."
                    ),
                )
            )

        if bool(payload.get("is_corrupt") or payload.get("unreadable")):
            issues.append(
                GeneratedValidationIssue(
                    rule_code="unreadable_document",
                    severity=ValidationSeverity.CRITICAL,
                    title="Unreadable or corrupt document",
                    description="The document could not be opened or read reliably.",
                    is_blocking=True,
                    remediation=(
                        "Request a clean replacement copy and keep any existing approved "
                        "operational document active."
                    ),
                )
            )

        confidence = self._as_float(
            payload.get("extraction_confidence")
            or payload.get("classification_confidence")
        )
        threshold = (
            self._as_float(payload.get("confidence_threshold"))
            or LOW_CONFIDENCE_THRESHOLD
        )
        if confidence is not None and confidence < threshold:
            issues.append(
                GeneratedValidationIssue(
                    rule_code="low_extraction_confidence",
                    severity=ValidationSeverity.WARNING,
                    title="Low extraction confidence",
                    description=(
                        f"Extraction confidence {confidence:.2f} is below the required "
                        f"threshold {threshold:.2f}."
                    ),
                    is_blocking=False,
                    remediation=(
                        "Review extracted values before using this document for packet "
                        "or billing decisions."
                    ),
                )
            )

        required_fields = [str(item) for item in payload.get("required_fields") or []]
        extracted = payload.get("extracted_fields") or {}
        if isinstance(extracted, list):
            extracted_names = {
                str(item.get("field_name") or item.get("name") or "")
                for item in extracted
                if isinstance(item, dict)
            }
        elif isinstance(extracted, dict):
            extracted_names = {
                key for key, value in extracted.items() if value not in (None, "")
            }
        else:
            extracted_names = set()
        missing_fields = sorted(
            field for field in required_fields if field not in extracted_names
        )
        if missing_fields:
            issues.append(
                GeneratedValidationIssue(
                    rule_code="missing_critical_extracted_values",
                    severity=ValidationSeverity.ERROR,
                    title="Missing critical extracted values",
                    description="Critical extracted values are missing: "
                    + ", ".join(missing_fields)
                    + ".",
                    is_blocking=True,
                    remediation=(
                        "Manually enter the missing values or request a clearer source "
                        "document."
                    ),
                )
            )

        mismatches = payload.get("validation_mismatches") or []
        if mismatches:
            issues.append(
                GeneratedValidationIssue(
                    rule_code="validation_mismatch",
                    severity=ValidationSeverity.ERROR,
                    title="Validation mismatch",
                    description="Extracted values do not match expected load or billing facts.",
                    is_blocking=True,
                    remediation=(
                        "Compare the document to the load record and correct the "
                        "document, extracted values, or load facts before submission."
                    ),
                )
            )

        if bool(payload.get("reupload_required") or payload.get("rejected")):
            issues.append(
                GeneratedValidationIssue(
                    rule_code="reupload_required",
                    severity=ValidationSeverity.ERROR,
                    title="Reupload required",
                    description="The document was rejected or marked as needing reupload.",
                    is_blocking=True,
                    remediation=(
                        "Request the replacement document while preserving existing "
                        "approved packet documents until an explicit replacement is accepted."
                    ),
                )
            )

        return issues

    @staticmethod
    def _as_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
