from __future__ import annotations

import uuid

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.domain.enums.billing_cycle import BillingCycle
from app.domain.models.service_plan import ServicePlan


class ServicePlanRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, service_plan: ServicePlan) -> ServicePlan:
        self.db.add(service_plan)
        self.db.flush()
        self.db.refresh(service_plan)
        return service_plan

    def get_by_id(self, service_plan_id: uuid.UUID) -> ServicePlan | None:
        stmt = select(ServicePlan).where(ServicePlan.id == service_plan_id)
        return self.db.scalar(stmt)

    def get_by_code(
        self,
        *,
        organization_id: uuid.UUID,
        code: str,
    ) -> ServicePlan | None:
        stmt = select(ServicePlan).where(
            ServicePlan.organization_id == organization_id,
            ServicePlan.code == code,
        )
        return self.db.scalar(stmt)

    def list(
        self,
        *,
        organization_id: uuid.UUID | None = None,
        billing_cycle: BillingCycle | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[ServicePlan], int]:
        stmt = select(ServicePlan)
        count_stmt: Select[tuple[int]] = select(func.count()).select_from(ServicePlan)

        if organization_id is not None:
            stmt = stmt.where(ServicePlan.organization_id == organization_id)
            count_stmt = count_stmt.where(ServicePlan.organization_id == organization_id)

        if billing_cycle is not None:
            stmt = stmt.where(ServicePlan.billing_cycle == billing_cycle)
            count_stmt = count_stmt.where(ServicePlan.billing_cycle == billing_cycle)

        if is_active is not None:
            stmt = stmt.where(ServicePlan.is_active == is_active)
            count_stmt = count_stmt.where(ServicePlan.is_active == is_active)

        if search:
            pattern = f"%{search.strip()}%"
            search_filter = or_(
                ServicePlan.name.ilike(pattern),
                ServicePlan.code.ilike(pattern),
                ServicePlan.description.ilike(pattern),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        total = self.db.scalar(count_stmt) or 0

        offset = max(page - 1, 0) * page_size
        stmt = stmt.order_by(ServicePlan.created_at.desc()).offset(offset).limit(page_size)

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