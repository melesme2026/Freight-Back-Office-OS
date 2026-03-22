from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.domain.models.extracted_field import ExtractedField


class ExtractedFieldRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, extracted_field: ExtractedField) -> ExtractedField:
        self.db.add(extracted_field)
        self.db.flush()
        self.db.refresh(extracted_field)
        return extracted_field

    def create_many(self, extracted_fields: list[ExtractedField]) -> list[ExtractedField]:
        self.db.add_all(extracted_fields)
        self.db.flush()
        for item in extracted_fields:
            self.db.refresh(item)
        return extracted_fields

    def get_by_id(self, field_id: uuid.UUID) -> ExtractedField | None:
        stmt = select(ExtractedField).where(ExtractedField.id == field_id)
        return self.db.scalar(stmt)

    def list(
        self,
        *,
        organization_id: uuid.UUID | None = None,
        document_id: uuid.UUID | None = None,
        load_id: uuid.UUID | None = None,
        field_name: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> tuple[list[ExtractedField], int]:
        stmt = select(ExtractedField)
        count_stmt: Select[tuple[int]] = select(func.count()).select_from(ExtractedField)

        if organization_id is not None:
            stmt = stmt.where(ExtractedField.organization_id == organization_id)
            count_stmt = count_stmt.where(ExtractedField.organization_id == organization_id)

        if document_id is not None:
            stmt = stmt.where(ExtractedField.document_id == document_id)
            count_stmt = count_stmt.where(ExtractedField.document_id == document_id)

        if load_id is not None:
            stmt = stmt.where(ExtractedField.load_id == load_id)
            count_stmt = count_stmt.where(ExtractedField.load_id == load_id)

        if field_name:
            stmt = stmt.where(ExtractedField.field_name == field_name)
            count_stmt = count_stmt.where(ExtractedField.field_name == field_name)

        total = self.db.scalar(count_stmt) or 0

        offset = max(page - 1, 0) * page_size
        stmt = (
            stmt.order_by(ExtractedField.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )

        items = list(self.db.scalars(stmt).all())
        return items, total

    def delete_for_document(self, document_id: uuid.UUID) -> int:
        items, _ = self.list(document_id=document_id, page=1, page_size=10000)
        count = len(items)
        for item in items:
            self.db.delete(item)
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