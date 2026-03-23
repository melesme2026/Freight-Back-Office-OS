from __future__ import annotations

from celery.schedules import crontab

from app.workers.celery_app import celery_app


celery_app.conf.beat_schedule = {
    "generate-recurring-invoices-daily": {
        "task": "app.workers.tasks.generate_recurring_invoices",
        "schedule": crontab(hour=1, minute=0),
    },
    "mark-overdue-invoices-daily": {
        "task": "app.workers.tasks.mark_overdue_invoices",
        "schedule": crontab(hour=2, minute=0),
    },
    "send-billing-reminders-daily": {
        "task": "app.workers.tasks.send_billing_reminders",
        "schedule": crontab(hour=8, minute=0),
    },
    "sync-payment-webhooks-every-15-minutes": {
        "task": "app.workers.tasks.sync_payment_webhooks",
        "schedule": crontab(minute="*/15"),
    },
}