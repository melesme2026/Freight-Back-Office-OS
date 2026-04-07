from __future__ import annotations

import uuid

from sqlalchemy import Select, delete, func, select
from sqlalchemy.orm import Session

from app.domain.models.extracted_field import ExtractedField


class ExtractedFieldRepository:
    DEFAULT_PAGE = 1
    DEFAULT_PAGE_SIZE = 100
    MAX_PAGE_SIZE = 500

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, extracted_field: ExtractedField) -> ExtractedField:
        self.db.add(extracted_field)
        self.db.flush()
        self.db.refresh(extracted_field)
        return extracted_field

    def create_many(self, extracted_fields: list[ExtractedField]) -> list[ExtractedField]:
        if not extracted_fields:
            return []

        self.db.add_all(extracted_fields)
        self.db.flush()

        for item in extracted_fields:
            self.db.refresh(item)

        return extracted_fields

    def get_by_id(self, field_id: uuid.UUID | str) -> ExtractedField | None:
        normalized_id = self._normalize_uuid(field_id, field_name="field_id")
        stmt = select(ExtractedField).where(ExtractedField.id == normalized_id)
        return self.db.scalar(stmt)

    def list(
        self,
        *,
        organization_id: uuid.UUID | str | None = None,
        document_id: uuid.UUID | str | None = None,
        load_id: uuid.UUID | str | None = None,
        field_name: str | None = None,
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[ExtractedField], int]:
        normalized_page = max(page, 1)
        normalized_page_size = min(max(page_size, 1), self.MAX_PAGE_SIZE)

        normalized_organization_id = (
            self._normalize_uuid(organization_id, field_name="organization_id")
            if organization_id is not None
            else None
        )
        normalized_document_id = (
            self._normalize_uuid(document_id, field_name="document_id")
            if document_id is not None
            else None
        )
        normalized_load_id = (
            self._normalize_uuid(load_id, field_name="load_id")
            if load_id is not None
            else None
        )
        normalized_field_name = field_name.strip() if field_name else None

        stmt = select(ExtractedField)
        count_stmt: Select[tuple[int]] = select(func.count()).select_from(ExtractedField)

        if normalized_organization_id is not None:
            stmt = stmt.where(ExtractedField.organization_id == normalized_organization_id)
            count_stmt = count_stmt.where(ExtractedField.organization_id == normalized_organization_id)

        if normalized_document_id is not None:
            stmt = stmt.where(ExtractedField.document_id == normalized_document_id)
            count_stmt = count_stmt.where(ExtractedField.document_id == normalized_document_id)

        if normalized_load_id is not None:
            stmt = stmt.where(ExtractedField.load_id == normalized_load_id)
            count_stmt = count_stmt.where(ExtractedField.load_id == normalized_load_id)

        if normalized_field_name:
            stmt = stmt.where(ExtractedField.field_name == normalized_field_name)
            count_stmt = count_stmt.where(ExtractedField.field_name == normalized_field_name)

        total = int(self.db.scalar(count_stmt) or 0)

        offset = (normalized_page - 1) * normalized_page_size
        stmt = (
            stmt.order_by(ExtractedField.created_at.desc())
            .offset(offset)
            .limit(normalized_page_size)
        )

        items = list(self.db.scalars(stmt).all())
        return items, total

    def delete_for_document(self, document_id: uuid.UUID | str) -> int:
        normalized_id = self._normalize_uuid(document_id, field_name="document_id")

        count_stmt = select(func.count()).where(ExtractedField.document_id == normalized_id)
        count = int(self.db.scalar(count_stmt) or 0)

        if count == 0:
            return 0

        stmt = delete(ExtractedField).where(ExtractedField.document_id == normalized_id)
        self.db.execute(stmt)
        self.db.flush()

        return count

    def update(self, extracted_field: ExtractedField) -> ExtractedField:
        self.db.add(extracted_field)
        self.db.flush()
        self.db.refresh(extracted_field)
        return extracted_field

    def delete(self, extracted_field: ExtractedField) -> None:
        self.db.delete(extracted_field)
        self.db.flush()

    def _normalize_uuid(self, value: uuid.UUID | str, *, field_name: str) -> uuid.UUID:
        if isinstance(value, uuid.UUID):
            return value

        try:
            return uuid.UUID(str(value))
        except ValueError as exc:
            raise ValueError(f"Invalid {field_name}: {value}") from exc