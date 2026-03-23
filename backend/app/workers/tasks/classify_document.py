from __future__ import annotations

from app.workers.celery_app import celery_app
from app.workers.queues import WorkerQueues


@celery_app.task(name="app.workers.tasks.classify_document", queue=WorkerQueues.CLASSIFICATION)
def classify_document(document_id: str) -> dict:
    return {
        "task": "classify_document",
        "document_id": document_id,
        "status": "queued",
    }