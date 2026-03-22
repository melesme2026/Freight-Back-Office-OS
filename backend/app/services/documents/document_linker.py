from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
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
    ):
        document = self.document_repo.get_by_id(document_id)
        if document is None:
            raise NotFoundError("Document not found", details={"document_id": document_id})

        load = self.load_repo.get_by_id(load_id)
        if load is None:
            raise NotFoundError("Load not found", details={"load_id": load_id})

        document.load_id = load.id
        self.document_repo.update(document)

        self._sync_load_document_flags(load)

        self.load_repo.update(load)
        return document

    def relink_documents_for_load(
        self,
        *,
        load_id: str,
    ) -> int:
        load = self.load_repo.get_by_id(load_id)
        if load is None:
            raise NotFoundError("Load not found", details={"load_id": load_id})

        documents, _ = self.document_repo.list(
            organization_id=load.organization_id,
            customer_account_id=load.customer_account_id,
            driver_id=load.driver_id,
            page=1,
            page_size=500,
        )

        linked = 0
        for document in documents:
            if document.load_id is None:
                document.load_id = load.id
                self.document_repo.update(document)
                linked += 1

        self._sync_load_document_flags(load)
        self.load_repo.update(load)
        return linked

    def _sync_load_document_flags(self, load) -> None:
        has_ratecon = False
        has_bol = False
        has_invoice = False

        for document in load.documents:
            doc_type = str(document.document_type)
            if doc_type == "rate_confirmation":
                has_ratecon = True
            elif doc_type == "bill_of_lading":
                has_bol = True
            elif doc_type == "invoice":
                has_invoice = True

        load.has_ratecon = has_ratecon
        load.has_bol = has_bol
        load.has_invoice = has_invoice
        load.documents_complete = has_ratecon and has_bol