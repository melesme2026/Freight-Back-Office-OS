from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
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
        staff_user_id: str,
        field_value_text: str | None = None,
        field_value_number: Any = None,
        field_value_date: Any = None,
        field_value_json: dict[str, Any] | list[Any] | None = None,
    ):
        extracted_field = self.extracted_field_repo.get_by_id(field_id)
        if extracted_field is None:
            raise NotFoundError("Extracted field not found", details={"field_id": field_id})

        extracted_field.field_value_text = field_value_text
        extracted_field.field_value_number = field_value_number
        extracted_field.field_value_date = field_value_date
        extracted_field.field_value_json = field_value_json
        extracted_field.is_human_corrected = True
        extracted_field.corrected_by_staff_user_id = staff_user_id
        extracted_field.corrected_at = datetime.now(timezone.utc).date()

        return self.extracted_field_repo.update(extracted_field)

    def resolve_validation_issue(
        self,
        *,
        issue_id: str,
        staff_user_id: str,
        resolution_notes: str | None = None,
    ):
        issue = self.validation_repo.get_by_id(issue_id)
        if issue is None:
            raise NotFoundError("Validation issue not found", details={"issue_id": issue_id})

        issue.is_resolved = True
        issue.resolved_by_staff_user_id = staff_user_id
        issue.resolved_at = datetime.now(timezone.utc)
        issue.resolution_notes = resolution_notes

        return self.validation_repo.update(issue)

    def mark_load_reviewed(
        self,
        *,
        load_id: str,
        staff_user_id: str,
    ):
        load = self.load_repo.get_by_id(load_id)
        if load is None:
            raise NotFoundError("Load not found", details={"load_id": load_id})

        load.last_reviewed_by = staff_user_id
        load.last_reviewed_at = datetime.now(timezone.utc)

        return self.load_repo.update(load)