from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.domain.enums.channel import Channel
from app.domain.enums.load_status import LoadStatus
from app.domain.models.load import Load


class LoadRepository:
    DEFAULT_PAGE = 1
    DEFAULT_PAGE_SIZE = 25
    MAX_PAGE_SIZE = 500

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, load: Load) -> Load:
        self.db.add(load)
        self.db.flush()
        self.db.refresh(load)
        return load

    def get_by_id(
        self,
        load_id: uuid.UUID | str,
        *,
        include_related: bool = False,
    ) -> Load | None:
        normalized_id = self._normalize_uuid(load_id, field_name="load_id")

        stmt = select(Load).where(Load.id == normalized_id)

        if include_related:
            stmt = self._apply_related_loads(stmt)

        return self.db.scalar(stmt)

    def get_by_invoice_number(
        self,
        *,
        organization_id: uuid.UUID | str,
        invoice_number: str,
    ) -> Load | None:
        normalized_organization_id = self._normalize_uuid(
            organization_id,
            field_name="organization_id",
        )

        stmt = select(Load).where(
            Load.organization_id == normalized_organization_id,
            Load.invoice_number == invoice_number,
        )
        return self.db.scalar(stmt)

    def get_by_load_number(
        self,
        *,
        organization_id: uuid.UUID | str,
        load_number: str,
    ) -> Load | None:
        normalized_organization_id = self._normalize_uuid(
            organization_id,
            field_name="organization_id",
        )

        stmt = select(Load).where(
            Load.organization_id == normalized_organization_id,
            Load.load_number == load_number,
        )
        return self.db.scalar(stmt)

    def list(
        self,
        *,
        organization_id: uuid.UUID | str | None = None,
        customer_account_id: uuid.UUID | str | None = None,
        driver_id: uuid.UUID | str | None = None,
        status: LoadStatus | None = None,
        source_channel: Channel | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        search: str | None = None,
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
        include_related: bool = False,
    ) -> tuple[list[Load], int]:
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
        normalized_search = search.strip() if search else None

        stmt = select(Load)
        count_stmt: Select[tuple[int]] = select(func.count()).select_from(Load)

        if include_related:
            stmt = self._apply_related_loads(stmt)

        if normalized_organization_id is not None:
            stmt = stmt.where(Load.organization_id == normalized_organization_id)
            count_stmt = count_stmt.where(Load.organization_id == normalized_organization_id)

        if normalized_customer_account_id is not None:
            stmt = stmt.where(Load.customer_account_id == normalized_customer_account_id)
            count_stmt = count_stmt.where(Load.customer_account_id == normalized_customer_account_id)

        if normalized_driver_id is not None:
            stmt = stmt.where(Load.driver_id == normalized_driver_id)
            count_stmt = count_stmt.where(Load.driver_id == normalized_driver_id)

        if status is not None:
            stmt = stmt.where(Load.status == status)
            count_stmt = count_stmt.where(Load.status == status)

        if source_channel is not None:
            stmt = stmt.where(Load.source_channel == source_channel)
            count_stmt = count_stmt.where(Load.source_channel == source_channel)

        if date_from is not None:
            stmt = stmt.where(Load.pickup_date >= date_from)
            count_stmt = count_stmt.where(Load.pickup_date >= date_from)

        if date_to is not None:
            stmt = stmt.where(Load.pickup_date <= date_to)
            count_stmt = count_stmt.where(Load.pickup_date <= date_to)

        if normalized_search:
            pattern = f"%{normalized_search}%"
            search_filter = or_(
                Load.load_number.ilike(pattern),
                Load.rate_confirmation_number.ilike(pattern),
                Load.bol_number.ilike(pattern),
                Load.invoice_number.ilike(pattern),
                Load.broker_name_raw.ilike(pattern),
                Load.broker_email_raw.ilike(pattern),
                Load.pickup_location.ilike(pattern),
                Load.delivery_location.ilike(pattern),
                Load.notes.ilike(pattern),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        total = int(self.db.scalar(count_stmt) or 0)

        offset = (normalized_page - 1) * normalized_page_size
        stmt = (
            stmt.order_by(Load.created_at.desc())
            .offset(offset)
            .limit(normalized_page_size)
        )

        items = list(self.db.scalars(stmt).all())
        return items, total

    def update(self, load: Load) -> Load:
        self.db.add(load)
        self.db.flush()
        self.db.refresh(load)
        return load

    def delete(self, load: Load) -> None:
        self.db.delete(load)
        self.db.flush()

    def _apply_related_loads(self, stmt: Select[tuple[Load]]) -> Select[tuple[Load]]:
        return stmt.options(
            selectinload(Load.driver),
            selectinload(Load.customer_account),
            selectinload(Load.broker),
            selectinload(Load.last_reviewed_by_user),
            selectinload(Load.documents),
            selectinload(Load.validation_issues),
            selectinload(Load.workflow_events),
        )

    def _normalize_uuid(self, value: uuid.UUID | str, *, field_name: str) -> uuid.UUID:
        if isinstance(value, uuid.UUID):
            return value

        try:
            return uuid.UUID(str(value))
        except ValueError as exc:
            raise ValueError(f"Invalid {field_name}: {value}") from exc