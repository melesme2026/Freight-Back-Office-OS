from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.config import Settings


@dataclass(frozen=True)
class SubscriptionPlan:
    key: str
    display_name: str
    monthly_price: int | None
    stripe_price_id: str | None
    feature_limits: dict[str, Any] = field(default_factory=dict)
    active: bool = True
    contact_sales: bool = False


def get_subscription_plans(settings: Settings) -> dict[str, SubscriptionPlan]:
    return {
        "starter": SubscriptionPlan(
            key="starter",
            display_name="Starter",
            monthly_price=199,
            stripe_price_id=settings.stripe_price_starter_monthly,
            feature_limits={"users": 3, "loads_per_month": 100},
        ),
        "growth": SubscriptionPlan(
            key="growth",
            display_name="Growth",
            monthly_price=499,
            stripe_price_id=settings.stripe_price_growth_monthly,
            feature_limits={"users": 15, "loads_per_month": 500},
        ),
        "fleet": SubscriptionPlan(
            key="fleet",
            display_name="Fleet / Enterprise",
            monthly_price=None,
            stripe_price_id=None,
            feature_limits={"users": "custom", "loads_per_month": "custom"},
            active=True,
            contact_sales=True,
        ),
    }


def get_subscription_plan(settings: Settings, plan_key: str) -> SubscriptionPlan | None:
    return get_subscription_plans(settings).get(plan_key.strip().lower())
