from __future__ import annotations

from decimal import Decimal

from app.core.exceptions import BillingError
from app.domain.models.service_plan import ServicePlan


class PricingService:
    def calculate_base_price(
        self,
        *,
        service_plan: ServicePlan,
    ) -> Decimal:
        return Decimal(service_plan.base_price)

    def calculate_usage_price(
        self,
        *,
        service_plan: ServicePlan,
        load_count: int = 0,
        driver_count: int = 0,
    ) -> Decimal:
        total = Decimal("0.00")

        if service_plan.per_load_price is not None:
            total += Decimal(service_plan.per_load_price) * Decimal(load_count)

        if service_plan.per_driver_price is not None:
            total += Decimal(service_plan.per_driver_price) * Decimal(driver_count)

        return total

    def calculate_total_price(
        self,
        *,
        service_plan: ServicePlan,
        load_count: int = 0,
        driver_count: int = 0,
    ) -> Decimal:
        return self.calculate_base_price(
            service_plan=service_plan
        ) + self.calculate_usage_price(
            service_plan=service_plan,
            load_count=load_count,
            driver_count=driver_count,
        )

    def validate_currency(
        self,
        *,
        service_plan: ServicePlan,
        currency_code: str,
    ) -> None:
        if service_plan.currency_code != currency_code:
            raise BillingError(
                "Currency mismatch for service plan pricing",
                details={
                    "service_plan_currency": service_plan.currency_code,
                    "requested_currency": currency_code,
                },
            )