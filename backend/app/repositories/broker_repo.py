from __future__ import annotations

import uuid

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.domain.models.broker import Broker


class BrokerRepository:
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
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[Broker], int]:
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

        offset = max(page - 1, 0) * page_size
        stmt = stmt.order_by(Broker.created_at.desc()).offset(offset).limit(page_size)

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