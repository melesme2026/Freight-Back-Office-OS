from __future__ import annotations

import uuid

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.domain.models.broker import Broker


class BrokerRepository:
    DEFAULT_PAGE = 1
    DEFAULT_PAGE_SIZE = 25
    MAX_PAGE_SIZE = 500

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, broker: Broker) -> Broker:
        self.db.add(broker)
        self.db.flush()
        self.db.refresh(broker)
        return broker

    def get_by_id(self, broker_id: uuid.UUID) -> Broker | None:
        stmt = select(Broker).where(Broker.id == broker_id)
        return self.db.scalar(stmt)

    def list(
        self,
        *,
        organization_id: uuid.UUID | None = None,
        mc_number: str | None = None,
        search: str | None = None,
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[Broker], int]:
        normalized_page = max(page, 1)
        normalized_page_size = min(max(page_size, 1), self.MAX_PAGE_SIZE)

        stmt = select(Broker)
        count_stmt: Select[tuple[int]] = select(func.count()).select_from(Broker)

        if organization_id is not None:
            stmt = stmt.where(Broker.organization_id == organization_id)
            count_stmt = count_stmt.where(Broker.organization_id == organization_id)

        if mc_number:
            stmt = stmt.where(Broker.mc_number == mc_number)
            count_stmt = count_stmt.where(Broker.mc_number == mc_number)

        if search:
            pattern = f"%{search.strip()}%"
            search_filter = or_(
                Broker.name.ilike(pattern),
                Broker.mc_number.ilike(pattern),
                Broker.email.ilike(pattern),
                Broker.phone.ilike(pattern),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        total = self.db.scalar(count_stmt) or 0

        offset = (normalized_page - 1) * normalized_page_size
        stmt = stmt.order_by(Broker.created_at.desc()).offset(offset).limit(normalized_page_size)

        items = list(self.db.scalars(stmt).all())
        return items, total

    def update(self, broker: Broker) -> Broker:
        self.db.add(broker)
        self.db.flush()
        self.db.refresh(broker)
        return broker

    def delete(self, broker: Broker) -> None:
        self.db.delete(broker)
        self.db.flush()