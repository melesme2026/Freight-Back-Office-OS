from __future__ import annotations

from app.workers.celery_app import celery_app
from app.workers.queues import WorkerQueues


@celery_app.task(name="app.workers.tasks.run_validation", queue=WorkerQueues.VALIDATION)
def run_validation(load_id: str) -> dict:
    return {
        "task": "run_validation",
        "load_id": load_id,
        "status": "queued",
    }