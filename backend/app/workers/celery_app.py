from __future__ import annotations

from celery import Celery

from app.core.config import get_settings


settings = get_settings()

celery_app = Celery(
    "freight_back_office_os",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.tasks.process_document",
        "app.workers.tasks.classify_document",
        "app.workers.tasks.extract_fields",
        "app.workers.tasks.run_validation",
        "app.workers.tasks.send_notification",
        "app.workers.tasks.reconcile_status",
        "app.workers.tasks.generate_recurring_invoices",
        "app.workers.tasks.collect_payment",
        "app.workers.tasks.mark_overdue_invoices",
        "app.workers.tasks.send_billing_reminders",
        "app.workers.tasks.sync_payment_webhooks",
        "app.workers.tasks.daily_follow_up_generation",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.timezone,
    enable_utc=True,
    task_track_started=True,
    task_time_limit=60 * 30,
    task_soft_time_limit=60 * 25,
)
