from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from app.domain.enums.document_type import DocumentType
from app.domain.enums.processing_status import ProcessingStatus
from app.domain.models.load_document import LoadDocument


class DocumentRepository:
    DEFAULT_PAGE = 1
    DEFAULT_PAGE_SIZE = 25
    MAX_PAGE_SIZE = 500

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, document: LoadDocument) -> LoadDocument:
        self.db.add(document)
        self.db.flush()
        self.db.refresh(document)
        return document

    def get_by_id(
        self,
        document_id: uuid.UUID | str,
        *,
        include_related: bool = False,
    ) -> LoadDocument | None:
        normalized_id = self._normalize_uuid(document_id, field_name="document_id")
        stmt = select(LoadDocument).where(LoadDocument.id == normalized_id)

        if include_related:
            stmt = self._apply_related(stmt)

        return self.db.scalar(stmt)

    def get_by_file_hash(
        self,
        *,
        file_hash_sha256: str,
        include_related: bool = False,
    ) -> LoadDocument | None:
        stmt = select(LoadDocument).where(
            LoadDocument.file_hash_sha256 == file_hash_sha256
        )

        if include_related:
            stmt = self._apply_related(stmt)

        return self.db.scalar(stmt)

    def list(
        self,
        *,
        organization_id: uuid.UUID | str | None = None,
        customer_account_id: uuid.UUID | str | None = None,
        driver_id: uuid.UUID | str | None = None,
        load_id: uuid.UUID | str | None = None,
        document_type: DocumentType | None = None,
        processing_status: ProcessingStatus | None = None,
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
        include_related: bool = False,
    ) -> tuple[list[LoadDocument], int]:
        normalized_page = max(page, 1)
        normalized_page_size = min(max(page_size, 1), self.MAX_PAGE_SIZE)

        normalized_organization_id = (
            self._normalize_uuid(organization_id, field_name="organization_id")
            if organization_id is not None
            else None
        )
        normalized_customer_account_id = (
            self._normalize_uuid(customer_account_id, field_name="customer_account_id")
            if customer_account_id is not None
            else None
        )
        normalized_driver_id = (
            self._normalize_uuid(driver_id, field_name="driver_id")
            if driver_id is not None
            else None
        )
        normalized_load_id = (
            self._normalize_uuid(load_id, field_name="load_id")
            if load_id is not None
            else None
        )

        stmt = select(LoadDocument)
        count_stmt: Select[tuple[int]] = select(func.count()).select_from(LoadDocument)

        if include_related:
            stmt = self._apply_related(stmt)

        if normalized_organization_id is not None:
            stmt = stmt.where(LoadDocument.organization_id == normalized_organization_id)
            count_stmt = count_stmt.where(
                LoadDocument.organization_id == normalized_organization_id
            )

        if normalized_customer_account_id is not None:
            stmt = stmt.where(LoadDocument.customer_account_id == normalized_customer_account_id)
            count_stmt = count_stmt.where(
                LoadDocument.customer_account_id == normalized_customer_account_id
            )

        if normalized_driver_id is not None:
            stmt = stmt.where(LoadDocument.driver_id == normalized_driver_id)
            count_stmt = count_stmt.where(LoadDocument.driver_id == normalized_driver_id)

        if normalized_load_id is not None:
            stmt = stmt.where(LoadDocument.load_id == normalized_load_id)
            count_stmt = count_stmt.where(LoadDocument.load_id == normalized_load_id)

        if document_type is not None:
            stmt = stmt.where(LoadDocument.document_type == document_type)
            count_stmt = count_stmt.where(LoadDocument.document_type == document_type)

        if processing_status is not None:
            stmt = stmt.where(LoadDocument.processing_status == processing_status)
            count_stmt = count_stmt.where(
                LoadDocument.processing_status == processing_status
            )

        total = int(self.db.scalar(count_stmt) or 0)

        offset = (normalized_page - 1) * normalized_page_size
        stmt = (
            stmt.order_by(LoadDocument.received_at.desc(), LoadDocument.created_at.desc())
            .offset(offset)
            .limit(normalized_page_size)
        )

        items = list(self.db.scalars(stmt).all())
        return items, total

    def update(self, document: LoadDocument) -> LoadDocument:
        self.db.add(document)
        self.db.flush()
        self.db.refresh(document)
        return document

    def delete(self, document: LoadDocument) -> None:
        self.db.delete(document)
        self.db.flush()

    def _apply_related(
        self,
        stmt: Select[tuple[LoadDocument]],
    ) -> Select[tuple[LoadDocument]]:
        return stmt.options(
            selectinload(LoadDocument.organization),
            selectinload(LoadDocument.driver),
            selectinload(LoadDocument.load),
            selectinload(LoadDocument.uploaded_by_staff_user),
            selectinload(LoadDocument.extracted_fields),
            selectinload(LoadDocument.validation_issues),
        )

    def _normalize_uuid(self, value: uuid.UUID | str, *, field_name: str) -> uuid.UUID:
        if isinstance(value, uuid.UUID):
            return value

        try:
            return uuid.UUID(str(value))
        except ValueError as exc:
            raise ValueError(f"Invalid {field_name}: {value}") from exc