from __future__ import annotations

from app.workers.celery_app import celery_app
from app.workers.queues import WorkerQueues


@celery_app.task(
    name="app.workers.tasks.collect_payment",
    queue=WorkerQueues.BILLING,
)
def collect_payment(payment_id: str) -> dict:
    return {
        "task": "collect_payment",
        "payment_id": payment_id,
        "status": "queued",
    }