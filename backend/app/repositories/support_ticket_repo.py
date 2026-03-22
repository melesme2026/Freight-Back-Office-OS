from __future__ import annotations

import uuid

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.domain.models.support_ticket import SupportTicket


class SupportTicketRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, support_ticket: SupportTicket) -> SupportTicket:
        self.db.add(support_ticket)
        self.db.flush()
        self.db.refresh(support_ticket)
        return support_ticket

    def get_by_id(self, ticket_id: uuid.UUID) -> SupportTicket | None:
        stmt = select(SupportTicket).where(SupportTicket.id == ticket_id)
        return self.db.scalar(stmt)

    def list(
        self,
        *,
        organization_id: uuid.UUID | None = None,
        customer_account_id: uuid.UUID | None = None,
        driver_id: uuid.UUID | None = None,
        load_id: uuid.UUID | None = None,
        assigned_to_staff_user_id: uuid.UUID | None = None,
        status: str | None = None,
        priority: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[SupportTicket], int]:
        stmt = select(SupportTicket)
        count_stmt: Select[tuple[int]] = select(func.count()).select_from(SupportTicket)

        if organization_id is not None:
            stmt = stmt.where(SupportTicket.organization_id == organization_id)
            count_stmt = count_stmt.where(SupportTicket.organization_id == organization_id)

        if customer_account_id is not None:
            stmt = stmt.where(SupportTicket.customer_account_id == customer_account_id)
            count_stmt = count_stmt.where(
                SupportTicket.customer_account_id == customer_account_id
            )

        if driver_id is not None:
            stmt = stmt.where(SupportTicket.driver_id == driver_id)
            count_stmt = count_stmt.where(SupportTicket.driver_id == driver_id)

        if load_id is not None:
            stmt = stmt.where(SupportTicket.load_id == load_id)
            count_stmt = count_stmt.where(SupportTicket.load_id == load_id)

        if assigned_to_staff_user_id is not None:
            stmt = stmt.where(
                SupportTicket.assigned_to_staff_user_id == assigned_to_staff_user_id
            )
            count_stmt = count_stmt.where(
                SupportTicket.assigned_to_staff_user_id == assigned_to_staff_user_id
            )

        if status:
            stmt = stmt.where(SupportTicket.status == status)
            count_stmt = count_stmt.where(SupportTicket.status == status)

        if priority:
            stmt = stmt.where(SupportTicket.priority == priority)
            count_stmt = count_stmt.where(SupportTicket.priority == priority)

        if search:
            pattern = f"%{search.strip()}%"
            search_filter = or_(
                SupportTicket.subject.ilike(pattern),
                SupportTicket.description.ilike(pattern),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        total = self.db.scalar(count_stmt) or 0

        offset = max(page - 1, 0) * page_size
        stmt = (
            stmt.order_by(SupportTicket.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )

        items = list(self.db.scalars(stmt).all())
        return items, total

    def update(self, support_ticket: SupportTicket) -> SupportTicket:
        self.db.add(support_ticket)
        self.db.flush()
        self.db.refresh(support_ticket)
        return support_ticket

    def delete(self, support_ticket: SupportTicket) -> None:
        self.db.delete(support_ticket)
        self.db.flush()