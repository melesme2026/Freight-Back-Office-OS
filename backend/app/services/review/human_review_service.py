from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, UnauthorizedError, ValidationError
from app.repositories.extracted_field_repo import ExtractedFieldRepository
from app.repositories.load_repo import LoadRepository
from app.repositories.validation_repo import ValidationRepository


class HumanReviewService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.load_repo = LoadRepository(db)
        self.extracted_field_repo = ExtractedFieldRepository(db)
        self.validation_repo = ValidationRepository(db)

    def correct_extracted_field(
        self,
        *,
        field_id: str,
        organization_id: str,
        staff_user_id: str,
        field_value_text: str | None = None,
        field_value_number: Any = None,
        field_value_date: Any = None,
        field_value_json: dict[str, Any] | list[Any] | None = None,
    ) -> Any:
        extracted_field = self.extracted_field_repo.get_by_id(field_id)
        if extracted_field is None:
            raise NotFoundError("Extracted field not found", details={"field_id": field_id})

        normalized_organization_id = self._normalize_required_uuid(
            organization_id,
            field_name="organization_id",
        )
        self._assert_same_organization(
            extracted_field,
            organization_id=normalized_organization_id,
            resource_name="Extracted field",
        )

        normalized_staff_user_id = self._normalize_required_uuid(
            staff_user_id,
            field_name="staff_user_id",
        )

        extracted_field.field_value_text = self._clean_text(field_value_text)
        extracted_field.field_value_number = field_value_number
        extracted_field.field_value_date = field_value_date
        extracted_field.field_value_json = field_value_json
        extracted_field.is_human_corrected = True
        extracted_field.corrected_by_staff_user_id = normalized_staff_user_id
        extracted_field.corrected_at = datetime.now(timezone.utc)

        updated = self.extracted_field_repo.update(extracted_field)
        return self.extracted_field_repo.get_by_id(updated.id) or updated

    def resolve_validation_issue(
        self,
        *,
        issue_id: str,
        organization_id: str,
        staff_user_id: str,
        resolution_notes: str | None = None,
    ) -> Any:
        issue = self.validation_repo.get_by_id(issue_id, include_related=True)
        if issue is None:
            raise NotFoundError("Validation issue not found", details={"issue_id": issue_id})

        normalized_organization_id = self._normalize_required_uuid(
            organization_id,
            field_name="organization_id",
        )
        self._assert_same_organization(
            issue,
            organization_id=normalized_organization_id,
            resource_name="Validation issue",
        )

        normalized_staff_user_id = self._normalize_required_uuid(
            staff_user_id,
            field_name="staff_user_id",
        )

        issue.is_resolved = True
        issue.resolved_by_staff_user_id = normalized_staff_user_id
        issue.resolved_at = datetime.now(timezone.utc)
        issue.resolution_notes = self._clean_text(resolution_notes)

        updated = self.validation_repo.update(issue)
        return self.validation_repo.get_by_id(updated.id, include_related=True) or updated

    def mark_load_reviewed(
        self,
        *,
        load_id: str,
        organization_id: str,
        staff_user_id: str,
    ) -> Any:
        load = self.load_repo.get_by_id(load_id, include_related=True)
        if load is None:
            raise NotFoundError("Load not found", details={"load_id": load_id})

        normalized_organization_id = self._normalize_required_uuid(
            organization_id,
            field_name="organization_id",
        )
        self._assert_same_organization(
            load,
            organization_id=normalized_organization_id,
            resource_name="Load",
        )

        normalized_staff_user_id = self._normalize_required_uuid(
            staff_user_id,
            field_name="staff_user_id",
        )

        load.last_reviewed_by = normalized_staff_user_id
        load.last_reviewed_at = datetime.now(timezone.utc)

        updated = self.load_repo.update(load)
        return self.load_repo.get_by_id(updated.id, include_related=True) or updated

    def _normalize_required_uuid(self, value: str, *, field_name: str) -> uuid.UUID:
        cleaned = self._clean_text(value)
        if not cleaned:
            raise ValidationError(
                f"{field_name} is required",
                details={field_name: value},
            )

        try:
            return uuid.UUID(cleaned)
        except ValueError as exc:
            raise ValidationError(
                f"Invalid {field_name}",
                details={field_name: value},
            ) from exc

    @staticmethod
    def _clean_text(value: str | None) -> str | None:
        if value is None:
            return None

        cleaned = str(value).strip()
        return cleaned or None

    def _assert_same_organization(
        self,
        resource: Any,
        *,
        organization_id: uuid.UUID,
        resource_name: str,
    ) -> None:
        resource_org_id = getattr(resource, "organization_id", None)
        if resource_org_id is None or str(resource_org_id) != str(organization_id):
            raise UnauthorizedError(f"{resource_name} is not in authenticated organization")
