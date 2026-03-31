from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.domain.enums.document_type import DocumentType
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
            "reason": "manually_linked",
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
        load_number = self._clean_hint(hints.get("load_number"))
        invoice_number = self._clean_hint(hints.get("invoice_number"))

        load = None
        reason = "no_match_found"

        if invoice_number:
            load = self.load_repo.get_by_invoice_number(
                organization_id=document.organization_id,
                invoice_number=invoice_number,
            )
            if load is not None:
                reason = "matched_by_invoice_number"

        if load is None and load_number:
            load = self.load_repo.get_by_load_number(
                organization_id=document.organization_id,
                load_number=load_number,
            )
            if load is not None:
                reason = "matched_by_load_number"

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
            "reason": reason,
        }

    def _update_load_document_flags(self, load: Load) -> None:
        documents, _ = self.document_repo.list(
            load_id=load.id,
            page=1,
            page_size=500,
        )

        has_ratecon = any(
            self._normalize_document_type(getattr(document, "document_type", None))
            == DocumentType.RATE_CONFIRMATION
            for document in documents
        )
        has_bol = any(
            self._normalize_document_type(getattr(document, "document_type", None))
            in {DocumentType.BILL_OF_LADING, DocumentType.PROOF_OF_DELIVERY}
            for document in documents
        )
        has_invoice = any(
            self._normalize_document_type(getattr(document, "document_type", None))
            == DocumentType.INVOICE
            for document in documents
        )

        load.has_ratecon = has_ratecon
        load.has_bol = has_bol
        load.has_invoice = has_invoice
        load.documents_complete = has_ratecon and has_bol and has_invoice

        self.load_repo.update(load)

    def _normalize_document_type(self, value: Any) -> DocumentType:
        if isinstance(value, DocumentType):
            return value

        normalized = str(value or "").strip().lower()

        aliases: dict[str, DocumentType] = {
            "rate_confirmation": DocumentType.RATE_CONFIRMATION,
            "ratecon": DocumentType.RATE_CONFIRMATION,
            "bill_of_lading": DocumentType.BILL_OF_LADING,
            "bol": DocumentType.BILL_OF_LADING,
            "proof_of_delivery": DocumentType.PROOF_OF_DELIVERY,
            "pod": DocumentType.PROOF_OF_DELIVERY,
            "invoice": DocumentType.INVOICE,
            "unknown": DocumentType.UNKNOWN,
        }

        return aliases.get(normalized, DocumentType.UNKNOWN)

    def _clean_hint(self, value: Any) -> str | None:
        if value is None:
            return None

        cleaned = str(value).strip()
        return cleaned or None