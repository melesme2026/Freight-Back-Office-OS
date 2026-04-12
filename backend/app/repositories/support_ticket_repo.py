from __future__ import annotations

import uuid

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.domain.models.support_ticket import SupportTicket


class SupportTicketRepository:
    DEFAULT_PAGE = 1
    DEFAULT_PAGE_SIZE = 50
    MAX_PAGE_SIZE = 500

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, support_ticket: SupportTicket) -> SupportTicket:
        self.db.add(support_ticket)
        self.db.flush()
        self.db.refresh(support_ticket)
        return support_ticket

    def get_by_id(self, ticket_id: uuid.UUID | str) -> SupportTicket | None:
        normalized_ticket_id = self._normalize_uuid(ticket_id, field_name="ticket_id")
        stmt = select(SupportTicket).where(SupportTicket.id == normalized_ticket_id)
        return self.db.scalar(stmt)

    def list(
        self,
        *,
        organization_id: uuid.UUID | str | None = None,
        customer_account_id: uuid.UUID | str | None = None,
        driver_id: uuid.UUID | str | None = None,
        load_id: uuid.UUID | str | None = None,
        assigned_to_staff_user_id: uuid.UUID | str | None = None,
        status: str | None = None,
        priority: str | None = None,
        search: str | None = None,
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[SupportTicket], int]:
        normalized_page = max(page, 1)
        normalized_page_size = min(max(page_size, 1), self.MAX_PAGE_SIZE)

        normalized_organization_id = (
            self._normalize_uuid(organization_id, field_name="organization_id")
            if organization_id is not None
            else None
        )
        normalized_customer_account_id = (
            self._normalize_uuid(customer_account_id, field_name="customer_account_id")
            if customer_account_id is not None
            else None
        )
        normalized_driver_id = (
            self._normalize_uuid(driver_id, field_name="driver_id")
            if driver_id is not None
            else None
        )
        normalized_load_id = (
            self._normalize_uuid(load_id, field_name="load_id")
            if load_id is not None
            else None
        )
        normalized_assigned_to_staff_user_id = (
            self._normalize_uuid(
                assigned_to_staff_user_id,
                field_name="assigned_to_staff_user_id",
            )
            if assigned_to_staff_user_id is not None
            else None
        )
        normalized_status = self._normalize_optional_text(status)
        normalized_priority = self._normalize_optional_text(priority)
        normalized_search = self._normalize_optional_text(search)

        stmt = select(SupportTicket)
        count_stmt: Select[tuple[int]] = select(func.count()).select_from(SupportTicket)

        if normalized_organization_id is not None:
            stmt = stmt.where(SupportTicket.organization_id == normalized_organization_id)
            count_stmt = count_stmt.where(SupportTicket.organization_id == normalized_organization_id)

        if normalized_customer_account_id is not None:
            stmt = stmt.where(SupportTicket.customer_account_id == normalized_customer_account_id)
            count_stmt = count_stmt.where(
                SupportTicket.customer_account_id == normalized_customer_account_id
            )

        if normalized_driver_id is not None:
            stmt = stmt.where(SupportTicket.driver_id == normalized_driver_id)
            count_stmt = count_stmt.where(SupportTicket.driver_id == normalized_driver_id)

        if normalized_load_id is not None:
            stmt = stmt.where(SupportTicket.load_id == normalized_load_id)
            count_stmt = count_stmt.where(SupportTicket.load_id == normalized_load_id)

        if normalized_assigned_to_staff_user_id is not None:
            stmt = stmt.where(
                SupportTicket.assigned_to_staff_user_id == normalized_assigned_to_staff_user_id
            )
            count_stmt = count_stmt.where(
                SupportTicket.assigned_to_staff_user_id == normalized_assigned_to_staff_user_id
            )

        if normalized_status:
            stmt = stmt.where(SupportTicket.status == normalized_status)
            count_stmt = count_stmt.where(SupportTicket.status == normalized_status)

        if normalized_priority:
            stmt = stmt.where(SupportTicket.priority == normalized_priority)
            count_stmt = count_stmt.where(SupportTicket.priority == normalized_priority)

        if normalized_search:
            pattern = f"%{normalized_search}%"
            search_filter = or_(
                SupportTicket.subject.ilike(pattern),
                SupportTicket.description.ilike(pattern),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        total = int(self.db.scalar(count_stmt) or 0)

        offset = (normalized_page - 1) * normalized_page_size
        stmt = (
            stmt.order_by(SupportTicket.created_at.desc())
            .offset(offset)
            .limit(normalized_page_size)
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