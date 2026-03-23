from __future__ import annotations

from app.workers.celery_app import celery_app
from app.workers.queues import WorkerQueues


@celery_app.task(name="app.workers.tasks.reconcile_status", queue=WorkerQueues.RECONCILIATION)
def reconcile_status(load_id: str) -> dict:
    return {
        "task": "reconcile_status",
        "load_id": load_id,
        "status": "queued",
    }