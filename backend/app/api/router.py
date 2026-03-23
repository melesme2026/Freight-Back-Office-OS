from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.billing_dashboard import router as billing_dashboard_router
from app.api.v1.billing_invoices import router as billing_invoices_router
from app.api.v1.brokers import router as brokers_router
from app.api.v1.customer_accounts import router as customer_accounts_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.documents import router as documents_router
from app.api.v1.drivers import router as drivers_router
from app.api.v1.health import router as health_router
from app.api.v1.loads import router as loads_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.onboarding import router as onboarding_router
from app.api.v1.organizations import router as organizations_router
from app.api.v1.payments import router as payments_router
from app.api.v1.referrals import router as referrals_router
from app.api.v1.review_queue import router as review_queue_router
from app.api.v1.service_plans import router as service_plans_router
from app.api.v1.staff_users import router as staff_users_router
from app.api.v1.subscriptions import router as subscriptions_router
from app.api.v1.support import router as support_router
from app.api.v1.webhooks_email import router as webhooks_email_router
from app.api.v1.webhooks_payment import router as webhooks_payment_router
from app.api.v1.webhooks_whatsapp import router as webhooks_whatsapp_router


api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router, tags=["auth"])
api_router.include_router(organizations_router, tags=["organizations"])
api_router.include_router(customer_accounts_router, tags=["customer-accounts"])
api_router.include_router(onboarding_router, tags=["onboarding"])
api_router.include_router(referrals_router, tags=["referrals"])
api_router.include_router(staff_users_router, tags=["staff-users"])
api_router.include_router(drivers_router, tags=["drivers"])
api_router.include_router(brokers_router, tags=["brokers"])
api_router.include_router(loads_router, tags=["loads"])
api_router.include_router(documents_router, tags=["documents"])
api_router.include_router(review_queue_router, tags=["review-queue"])
api_router.include_router(dashboard_router, tags=["dashboard"])
api_router.include_router(notifications_router, tags=["notifications"])
api_router.include_router(service_plans_router, tags=["service-plans"])
api_router.include_router(subscriptions_router, tags=["subscriptions"])
api_router.include_router(billing_invoices_router, tags=["billing-invoices"])
api_router.include_router(payments_router, tags=["payments"])
api_router.include_router(billing_dashboard_router, tags=["billing-dashboard"])
api_router.include_router(support_router, tags=["support"])
api_router.include_router(webhooks_whatsapp_router, tags=["webhooks-whatsapp"])
api_router.include_router(webhooks_email_router, tags=["webhooks-email"])
api_router.include_router(webhooks_payment_router, tags=["webhooks-payment"])
api_router.include_router(health_router, tags=["health"])