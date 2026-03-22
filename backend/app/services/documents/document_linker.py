from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.domain.models.load import Load
from app.repositories.document_repo import DocumentRepository
from app.repositories.load_repo import LoadRepository


class DocumentLinker:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.document_repo = DocumentRepository(db)
        self.load_repo = LoadRepository(db)

    def link_document_to_load(
        self,
        *,
        document_id: str,
        load_id: str,
    ) -> dict[str, Any]:
        document = self.document_repo.get_by_id(document_id)
        if document is None:
            raise NotFoundError("Document not found", details={"document_id": document_id})

        load = self.load_repo.get_by_id(load_id)
        if load is None:
            raise NotFoundError("Load not found", details={"load_id": load_id})

        document.load_id = load.id
        self.document_repo.update(document)

        self._update_load_document_flags(load)

        return {
            "document_id": str(document.id),
            "load_id": str(load.id),
            "linked": True,
        }

    def auto_link_document(
        self,
        *,
        document_id: str,
        hints: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        document = self.document_repo.get_by_id(document_id)
        if document is None:
            raise NotFoundError("Document not found", details={"document_id": document_id})

        if document.load_id:
            return {
                "document_id": str(document.id),
                "load_id": str(document.load_id),
                "linked": True,
                "reason": "already_linked",
            }

        hints = hints or {}

        load_number = hints.get("load_number")
        invoice_number = hints.get("invoice_number")

        load = None

        if invoice_number:
            load = self.load_repo.get_by_invoice_number(
                organization_id=document.organization_id,
                invoice_number=invoice_number,
            )

        # NOTE: extend here with more intelligent matching later (e.g., load_number, fuzzy match)

        if load is None:
            return {
                "document_id": str(document.id),
                "linked": False,
                "reason": "no_match_found",
            }

        document.load_id = load.id
        self.document_repo.update(document)

        self._update_load_document_flags(load)

        return {
            "document_id": str(document.id),
            "load_id": str(load.id),
            "linked": True,
            "reason": "matched_by_invoice_number",
        }

    def _update_load_document_flags(self, load: Load) -> None:
        # Minimal placeholder — expand later with full document completeness logic
        if load.has_invoice is False:
            load.has_invoice = True

        self.load_repo.update(load)