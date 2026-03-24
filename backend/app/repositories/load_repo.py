from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.domain.enums.channel import Channel
from app.domain.enums.load_status import LoadStatus
from app.domain.models.load import Load


class LoadRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, load: Load) -> Load:
        self.db.add(load)
        self.db.flush()
        self.db.refresh(load)
        return load

    def get_by_id(self, load_id: uuid.UUID | str) -> Load | None:
        normalized_id = self._normalize_uuid(load_id, field_name="load_id")
        stmt = select(Load).where(Load.id == normalized_id)
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
        organization_id: uuid.UUID | None = None,
        customer_account_id: uuid.UUID | None = None,
        driver_id: uuid.UUID | None = None,
        status: LoadStatus | None = None,
        source_channel: Channel | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[Load], int]:
        stmt = select(Load)
        count_stmt: Select[tuple[int]] = select(func.count()).select_from(Load)

        if organization_id is not None:
            stmt = stmt.where(Load.organization_id == organization_id)
            count_stmt = count_stmt.where(Load.organization_id == organization_id)

        if customer_account_id is not None:
            stmt = stmt.where(Load.customer_account_id == customer_account_id)
            count_stmt = count_stmt.where(Load.customer_account_id == customer_account_id)

        if driver_id is not None:
            stmt = stmt.where(Load.driver_id == driver_id)
            count_stmt = count_stmt.where(Load.driver_id == driver_id)

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

        if search:
            pattern = f"%{search.strip()}%"
            search_filter = or_(
                Load.load_number.ilike(pattern),
                Load.rate_confirmation_number.ilike(pattern),
                Load.bol_number.ilike(pattern),
                Load.invoice_number.ilike(pattern),
                Load.broker_name_raw.ilike(pattern),
                Load.pickup_location.ilike(pattern),
                Load.delivery_location.ilike(pattern),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        total = self.db.scalar(count_stmt) or 0

        offset = max(page - 1, 0) * page_size
        stmt = stmt.order_by(Load.created_at.desc()).offset(offset).limit(page_size)

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

    def _normalize_uuid(self, value: uuid.UUID | str, *, field_name: str) -> uuid.UUID:
        if isinstance(value, uuid.UUID):
            return value

        try:
            return uuid.UUID(str(value))
        except ValueError as exc:
            raise ValueError(f"Invalid {field_name}: {value}") from exc