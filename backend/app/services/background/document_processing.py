from __future__ import annotations

import logging
from typing import Any

from app.core.database import db_session
from app.domain.enums.processing_status import ProcessingStatus
from app.services.ai.extraction_service import ExtractionService
from app.services.background.job_queue import job_queue
from app.services.documents.document_service import DocumentService

logger = logging.getLogger(__name__)


def enqueue_document_extraction(
    *,
    document_id: str,
    organization_id: str,
    force: bool = False,
) -> dict[str, Any]:
    record = job_queue.enqueue(
        job_type="document_extraction",
        organization_id=organization_id,
        entity_type="document",
        entity_id=document_id,
        idempotency_key=f"document_extraction:{organization_id}:{document_id}:{int(force)}",
        max_attempts=3,
    )
    return record.as_dict()


def run_document_extraction_job(*, job_id: str, document_id: str, force: bool = False) -> None:
    def _work() -> dict[str, Any]:
        with db_session() as session:
            document_service = DocumentService(session)
            document = document_service.get_document(document_id)
            document_service.mark_processing(
                document_id=document_id,
                processing_status=ProcessingStatus.IN_PROGRESS,
            )
            try:
                result = ExtractionService(session).extract_document(
                    document_id=document_id, force=force
                )
            except Exception:
                logger.exception(
                    "Document extraction failed without blocking upload",
                    extra={
                        "document_id": document_id,
                        "organization_id": str(document.organization_id),
                    },
                )
                try:
                    document_service.mark_processing(
                        document_id=document_id,
                        processing_status=ProcessingStatus.FAILED,
                    )
                except Exception:
                    logger.exception(
                        "Failed to persist document extraction failure status",
                        extra={"document_id": document_id},
                    )
                raise
            return {
                "document_id": result.get("document_id", document_id),
                "processing_status": ProcessingStatus.COMPLETED.value,
            }

    job_queue.run(job_id, _work)
