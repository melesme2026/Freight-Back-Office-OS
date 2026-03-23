from __future__ import annotations

from app.workers.celery_app import celery_app
from app.workers.queues import WorkerQueues


@celery_app.task(name="app.workers.tasks.extract_fields", queue=WorkerQueues.EXTRACTION)
def extract_fields(document_id: str) -> dict:
    return {
        "task": "extract_fields",
        "document_id": document_id,
        "status": "queued",
    }