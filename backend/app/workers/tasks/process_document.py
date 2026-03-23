from __future__ import annotations

from app.workers.celery_app import celery_app
from app.workers.queues import WorkerQueues


@celery_app.task(name="app.workers.tasks.process_document", queue=WorkerQueues.DOCUMENT_PROCESSING)
def process_document(document_id: str) -> dict:
    return {
        "task": "process_document",
        "document_id": document_id,
        "status": "queued",
    }