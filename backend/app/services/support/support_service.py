from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
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
            organization_id=self._require_text(organization_id, field_name="organization_id"),
            customer_account_id=self._clean_text(customer_account_id),
            driver_id=self._clean_text(driver_id),
            load_id=self._clean_text(load_id),
            assigned_to_staff_user_id=self._clean_text(assigned_to_staff_user_id),
            subject=self._require_text(subject, field_name="subject"),
            description=self._require_text(description, field_name="description"),
            status="open",
            priority=self._normalize_priority(priority),
            resolved_at=None,
        )
        created = self.support_ticket_repo.create(ticket)
        return self.support_ticket_repo.get_by_id(created.id) or created

    def get_ticket(self, ticket_id: str) -> SupportTicket:
        normalized_ticket_id = self._require_text(ticket_id, field_name="ticket_id")
        ticket = self.support_ticket_repo.get_by_id(normalized_ticket_id)
        if ticket is None:
            raise NotFoundError("Support ticket not found", details={"ticket_id": normalized_ticket_id})
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
            organization_id=self._clean_text(organization_id),
            customer_account_id=self._clean_text(customer_account_id),
            driver_id=self._clean_text(driver_id),
            load_id=self._clean_text(load_id),
            assigned_to_staff_user_id=self._clean_text(assigned_to_staff_user_id),
            status=self._normalize_status(status, allow_none=True),
            priority=self._normalize_priority(priority, allow_none=True),
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

            if field == "subject":
                setattr(ticket, field, self._require_text(value, field_name="subject"))
                continue

            if field == "description":
                setattr(ticket, field, self._require_text(value, field_name="description"))
                continue

            if field == "status":
                setattr(ticket, field, self._normalize_status(value))
                continue

            if field == "priority":
                setattr(ticket, field, self._normalize_priority(value))
                continue

            setattr(ticket, field, value)

        if getattr(ticket, "status", None) == "resolved":
            if getattr(ticket, "resolved_at", None) is None:
                ticket.resolved_at = datetime.now(timezone.utc)
        else:
            ticket.resolved_at = None

        updated = self.support_ticket_repo.update(ticket)
        return self.support_ticket_repo.get_by_id(updated.id) or updated

    @staticmethod
    def _clean_text(value: str | None) -> str | None:
        if value is None:
            return None

        cleaned = str(value).strip()
        return cleaned or None

    def _require_text(self, value: str | None, *, field_name: str) -> str:
        cleaned = self._clean_text(value)
        if not cleaned:
            raise ValidationError(
                f"{field_name} is required",
                details={field_name: value},
            )
        return cleaned

    def _normalize_status(
        self,
        value: str | None,
        *,
        allow_none: bool = False,
    ) -> str | None:
        if value is None:
            return None if allow_none else "open"

        normalized = self._clean_text(value)
        if normalized is None:
            return None if allow_none else "open"

        lowered = normalized.lower()
        allowed = {"open", "in_progress", "pending", "resolved", "closed"}

        if lowered not in allowed:
            raise ValidationError(
                "Invalid support ticket status",
                details={"status": value},
            )

        return lowered

    def _normalize_priority(
        self,
        value: str | None,
        *,
        allow_none: bool = False,
    ) -> str | None:
        if value is None:
            return None if allow_none else "normal"

        normalized = self._clean_text(value)
        if normalized is None:
            return None if allow_none else "normal"

        lowered = normalized.lower()
        allowed = {"low", "normal", "high", "urgent"}

        if lowered not in allowed:
            raise ValidationError(
                "Invalid support ticket priority",
                details={"priority": value},
            )

        return lowered