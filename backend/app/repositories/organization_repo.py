from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models.organization import Organization


class OrganizationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, organization: Organization) -> Organization:
        self.db.add(organization)
        self.db.flush()
        self.db.refresh(organization)
        return organization

    def get_by_id(self, organization_id: uuid.UUID) -> Organization | None:
        stmt = select(Organization).where(Organization.id == organization_id)
        return self.db.scalar(stmt)

    def get_by_slug(self, slug: str) -> Organization | None:
        stmt = select(Organization).where(Organization.slug == slug)
        return self.db.scalar(stmt)

    def list_all(self) -> list[Organization]:
        stmt = select(Organization).order_by(Organization.created_at.desc())
        return list(self.db.scalars(stmt).all())

    def update(self, organization: Organization) -> Organization:
        self.db.add(organization)
        self.db.flush()
        self.db.refresh(organization)
        return organization

    def delete(self, organization: Organization) -> None:
        self.db.delete(organization)
        self.db.flush()