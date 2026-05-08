from __future__ import annotations

from datetime import datetime, timezone

from app.core.config import Settings, get_settings
from app.core.exceptions import BillingError
from app.domain.models.organization import Organization
from app.services.billing.subscription_plans import get_subscription_plan

ACTIVE_STATUSES = {"active", "trialing"}
BILLING_SAFE_FEATURES = {"billing", "billing_status", "settings"}


def can_access_feature(
    org: Organization,
    feature_key: str,
    *,
    settings: Settings | None = None,
) -> bool:
    app_settings = settings or get_settings()
    normalized_feature = feature_key.strip().lower()
    if normalized_feature in BILLING_SAFE_FEATURES:
        return True
    if not app_settings.billing_enforcement_enabled:
        return True
    status = (org.subscription_status or "none").strip().lower()
    if status in ACTIVE_STATUSES:
        if status == "trialing" and org.trial_end is not None:
            trial_end = org.trial_end
            if trial_end.tzinfo is None:
                trial_end = trial_end.replace(tzinfo=timezone.utc)
            return trial_end >= datetime.now(timezone.utc)
        return True
    return False


def require_active_subscription(
    org: Organization,
    *,
    feature_key: str = "app",
    settings: Settings | None = None,
) -> None:
    if can_access_feature(org, feature_key, settings=settings):
        return
    raise BillingError(
        "Active subscription required",
        details={
            "subscription_status": org.subscription_status,
            "plan_key": org.plan_key,
            "enforcement_enabled": (settings or get_settings()).billing_enforcement_enabled,
        },
    )


def allowed_features(org: Organization, *, settings: Settings | None = None) -> dict[str, bool]:
    app_settings = settings or get_settings()
    plan = get_subscription_plan(app_settings, org.plan_key or "none")
    base_features = {
        "billing": True,
        "settings": True,
        "loads": can_access_feature(org, "loads", settings=app_settings),
        "documents": can_access_feature(org, "documents", settings=app_settings),
        "accounting_exports": can_access_feature(org, "accounting_exports", settings=app_settings),
        "factoring": can_access_feature(org, "factoring", settings=app_settings),
    }
    if plan and plan.contact_sales:
        base_features["contact_sales"] = True
    return base_features
