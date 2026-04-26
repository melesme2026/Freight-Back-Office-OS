from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models.carrier_profile import CarrierProfile


class CarrierProfileRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_organization_id(self, organization_id: uuid.UUID | str) -> CarrierProfile | None:
        stmt = select(CarrierProfile).where(CarrierProfile.organization_id == uuid.UUID(str(organization_id)))
        return self.db.scalar(stmt)

    def create(self, item: CarrierProfile) -> CarrierProfile:
        self.db.add(item)
        self.db.flush()
        self.db.refresh(item)
        return item

    def update(self, item: CarrierProfile) -> CarrierProfile:
        self.db.add(item)
        self.db.flush()
        self.db.refresh(item)
        return item
