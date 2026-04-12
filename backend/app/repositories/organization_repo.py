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

    def get_by_id(self, organization_id: uuid.UUID | str) -> Organization | None:
        normalized_organization_id = self._normalize_uuid(
            organization_id,
            field_name="organization_id",
        )
        stmt = select(Organization).where(Organization.id == normalized_organization_id)
        return self.db.scalar(stmt)

    def get_by_slug(self, slug: str) -> Organization | None:
        normalized_slug = self._normalize_required_text(slug, field_name="slug").lower()
        stmt = select(Organization).where(Organization.slug == normalized_slug)
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

    def _normalize_uuid(self, value: uuid.UUID | str, *, field_name: str) -> uuid.UUID:
        if isinstance(value, uuid.UUID):
            return value

        try:
            return uuid.UUID(str(value))
        except ValueError as exc:
            raise ValueError(f"Invalid {field_name}: {value}") from exc

    @staticmethod
    def _normalize_required_text(value: str, *, field_name: str) -> str:
        normalized = str(value).strip()
        if not normalized:
            raise ValueError(f"{field_name} is required")
        return normalized