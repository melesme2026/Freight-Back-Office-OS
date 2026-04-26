from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.v1.auth import router as auth_router
from app.api.v1.billing_dashboard import router as billing_dashboard_router
from app.api.v1.billing_invoices import router as billing_invoices_router
from app.api.v1.carrier_profile import router as carrier_profile_router
from app.api.v1.brokers import router as brokers_router
from app.api.v1.customer_accounts import router as customer_accounts_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.documents import router as documents_router
from app.api.v1.drivers import router as drivers_router
from app.api.v1.health import router as health_router
from app.api.v1.loads import router as loads_router
from app.api.v1.load_payment_reconciliation import router as load_payment_reconciliation_router
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
from app.core.config import get_settings
from app.core.security import get_current_token_payload


settings = get_settings()

api_router = APIRouter(prefix=settings.api_v1_prefix)

# Core / system
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router, tags=["auth"])

protected_dependencies = [Depends(get_current_token_payload)]

# Tenant / account setup
api_router.include_router(organizations_router, tags=["organizations"], dependencies=protected_dependencies)
api_router.include_router(customer_accounts_router, tags=["customer-accounts"], dependencies=protected_dependencies)
api_router.include_router(onboarding_router, tags=["onboarding"], dependencies=protected_dependencies)
api_router.include_router(referrals_router, tags=["referrals"], dependencies=protected_dependencies)
api_router.include_router(staff_users_router, tags=["staff-users"], dependencies=protected_dependencies)

# Operational entities
api_router.include_router(drivers_router, tags=["drivers"], dependencies=protected_dependencies)
api_router.include_router(brokers_router, tags=["brokers"], dependencies=protected_dependencies)
api_router.include_router(carrier_profile_router, tags=["carrier-profile"], dependencies=protected_dependencies)
api_router.include_router(loads_router, tags=["loads"], dependencies=protected_dependencies)
api_router.include_router(load_payment_reconciliation_router, tags=["load-payment-reconciliation"], dependencies=protected_dependencies)
api_router.include_router(documents_router, tags=["documents"], dependencies=protected_dependencies)
api_router.include_router(review_queue_router, tags=["review-queue"], dependencies=protected_dependencies)
api_router.include_router(notifications_router, tags=["notifications"], dependencies=protected_dependencies)
api_router.include_router(support_router, tags=["support"], dependencies=protected_dependencies)

# Product / billing
api_router.include_router(service_plans_router, tags=["service-plans"], dependencies=protected_dependencies)
api_router.include_router(subscriptions_router, tags=["subscriptions"], dependencies=protected_dependencies)
api_router.include_router(billing_invoices_router, tags=["billing-invoices"], dependencies=protected_dependencies)
api_router.include_router(payments_router, tags=["payments"], dependencies=protected_dependencies)
api_router.include_router(billing_dashboard_router, tags=["billing-dashboard"], dependencies=protected_dependencies)

# Dashboards
api_router.include_router(dashboard_router, tags=["dashboard"], dependencies=protected_dependencies)

# Webhooks
api_router.include_router(webhooks_whatsapp_router, tags=["webhooks-whatsapp"])
api_router.include_router(webhooks_email_router, tags=["webhooks-email"])
api_router.include_router(webhooks_payment_router, tags=["webhooks-payment"])
