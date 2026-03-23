from __future__ import annotations

from app.workers.celery_app import celery_app
from app.workers.queues import WorkerQueues


@celery_app.task(
    name="app.workers.tasks.sync_payment_webhooks",
    queue=WorkerQueues.WEBHOOKS,
)
def sync_payment_webhooks() -> dict:
    return {
        "task": "sync_payment_webhooks",
        "status": "queued",
    }