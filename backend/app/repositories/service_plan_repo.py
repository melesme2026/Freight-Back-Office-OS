from __future__ import annotations

import uuid

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.domain.enums.billing_cycle import BillingCycle
from app.domain.models.service_plan import ServicePlan


class ServicePlanRepository:
    DEFAULT_PAGE = 1
    DEFAULT_PAGE_SIZE = 25
    MAX_PAGE_SIZE = 500

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, service_plan: ServicePlan) -> ServicePlan:
        self.db.add(service_plan)
        self.db.flush()
        self.db.refresh(service_plan)
        return service_plan

    def get_by_id(self, service_plan_id: uuid.UUID | str) -> ServicePlan | None:
        normalized_service_plan_id = self._normalize_uuid(
            service_plan_id,
            field_name="service_plan_id",
        )
        stmt = select(ServicePlan).where(ServicePlan.id == normalized_service_plan_id)
        return self.db.scalar(stmt)

    def get_by_code(
        self,
        *,
        organization_id: uuid.UUID | str,
        code: str,
    ) -> ServicePlan | None:
        normalized_organization_id = self._normalize_uuid(
            organization_id,
            field_name="organization_id",
        )
        normalized_code = self._normalize_required_text(code, field_name="code")

        stmt = select(ServicePlan).where(
            ServicePlan.organization_id == normalized_organization_id,
            ServicePlan.code == normalized_code,
        )
        return self.db.scalar(stmt)

    def list(
        self,
        *,
        organization_id: uuid.UUID | str | None = None,
        billing_cycle: BillingCycle | str | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[ServicePlan], int]:
        normalized_page = max(page, 1)
        normalized_page_size = min(max(page_size, 1), self.MAX_PAGE_SIZE)

        normalized_organization_id = (
            self._normalize_uuid(organization_id, field_name="organization_id")
            if organization_id is not None
            else None
        )
        normalized_billing_cycle = self._normalize_billing_cycle(billing_cycle)
        normalized_search = self._normalize_optional_text(search)

        stmt = select(ServicePlan)
        count_stmt: Select[tuple[int]] = select(func.count()).select_from(ServicePlan)

        if normalized_organization_id is not None:
            stmt = stmt.where(ServicePlan.organization_id == normalized_organization_id)
            count_stmt = count_stmt.where(ServicePlan.organization_id == normalized_organization_id)

        if normalized_billing_cycle is not None:
            stmt = stmt.where(ServicePlan.billing_cycle == normalized_billing_cycle)
            count_stmt = count_stmt.where(ServicePlan.billing_cycle == normalized_billing_cycle)

        if is_active is not None:
            stmt = stmt.where(ServicePlan.is_active == is_active)
            count_stmt = count_stmt.where(ServicePlan.is_active == is_active)

        if normalized_search:
            pattern = f"%{normalized_search}%"
            search_filter = or_(
                ServicePlan.name.ilike(pattern),
                ServicePlan.code.ilike(pattern),
                ServicePlan.description.ilike(pattern),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        total = int(self.db.scalar(count_stmt) or 0)

        offset = (normalized_page - 1) * normalized_page_size
        stmt = (
            stmt.order_by(ServicePlan.created_at.desc())
            .offset(offset)
            .limit(normalized_page_size)
        )

        items = list(self.db.scalars(stmt).all())
        return items, total

    def update(self, service_plan: ServicePlan) -> ServicePlan:
        self.db.add(service_plan)
        self.db.flush()
        self.db.refresh(service_plan)
        return service_plan

    def delete(self, service_plan: ServicePlan) -> None:
        self.db.delete(service_plan)
        self.db.flush()

    def _normalize_uuid(self, value: uuid.UUID | str, *, field_name: str) -> uuid.UUID:
        if isinstance(value, uuid.UUID):
            return value

        try:
            return uuid.UUID(str(value))
        except ValueError as exc:
            raise ValueError(f"Invalid {field_name}: {value}") from exc

    @staticmethod
    def _normalize_optional_text(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    def _normalize_required_text(self, value: str, *, field_name: str) -> str:
        normalized = self._normalize_optional_text(value)
        if not normalized:
            raise ValueError(f"{field_name} is required")
        return normalized

    def _normalize_billing_cycle(
        self,
        value: BillingCycle | str | None,
    ) -> BillingCycle | None:
        if value is None:
            return None

        if isinstance(value, BillingCycle):
            return value

        normalized = str(value).strip().lower()

        for cycle in BillingCycle:
            if normalized == cycle.value.lower():
                return cycle
            if normalized == cycle.name.lower():
                return cycle

        raise ValueError(f"Invalid billing_cycle: {value}")