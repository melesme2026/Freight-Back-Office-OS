from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.domain.models.support_ticket import SupportTicket
from app.repositories.support_ticket_repo import SupportTicketRepository


class SupportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.support_ticket_repo = SupportTicketRepository(db)

    def create_ticket(
        self,
        *,
        organization_id: str,
        subject: str,
        description: str,
        customer_account_id: str | None = None,
        driver_id: str | None = None,
        load_id: str | None = None,
        priority: str = "normal",
        assigned_to_staff_user_id: str | None = None,
    ) -> SupportTicket:
        ticket = SupportTicket(
            organization_id=organization_id,
            customer_account_id=customer_account_id,
            driver_id=driver_id,
            load_id=load_id,
            assigned_to_staff_user_id=assigned_to_staff_user_id,
            subject=self._clean_text(subject),
            description=self._clean_text(description),
            status="open",
            priority=self._clean_text(priority) or "normal",
            resolved_at=None,
        )
        return self.support_ticket_repo.create(ticket)

    def get_ticket(self, ticket_id: str) -> SupportTicket:
        ticket = self.support_ticket_repo.get_by_id(ticket_id)
        if ticket is None:
            raise NotFoundError("Support ticket not found", details={"ticket_id": ticket_id})
        return ticket

    def list_tickets(
        self,
        *,
        organization_id: str | None = None,
        customer_account_id: str | None = None,
        driver_id: str | None = None,
        load_id: str | None = None,
        assigned_to_staff_user_id: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[SupportTicket], int]:
        return self.support_ticket_repo.list(
            organization_id=organization_id,
            customer_account_id=customer_account_id,
            driver_id=driver_id,
            load_id=load_id,
            assigned_to_staff_user_id=assigned_to_staff_user_id,
            status=self._clean_text(status),
            priority=self._clean_text(priority),
            search=self._clean_text(search),
            page=page,
            page_size=page_size,
        )

    def update_ticket(
        self,
        *,
        ticket_id: str,
        **updates,
    ) -> SupportTicket:
        ticket = self.get_ticket(ticket_id)

        for field, value in updates.items():
            if not hasattr(ticket, field) or value is None:
                continue

            if field in {"subject", "description", "status", "priority"}:
                setattr(ticket, field, self._clean_text(value))
            else:
                setattr(ticket, field, value)

        if getattr(ticket, "status", None) != "resolved":
            ticket.resolved_at = None

        return self.support_ticket_repo.update(ticket)

    @staticmethod
    def _clean_text(value: str | None) -> str | None:
        if value is None:
            return None

        cleaned = str(value).strip()
        return cleaned or None