from __future__ import annotations

import uuid

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.domain.models.referral import Referral


class ReferralRepository:
    DEFAULT_PAGE = 1
    DEFAULT_PAGE_SIZE = 25
    MAX_PAGE_SIZE = 500

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, referral: Referral) -> Referral:
        self.db.add(referral)
        self.db.flush()
        self.db.refresh(referral)
        return referral

    def get_by_id(self, referral_id: uuid.UUID | str) -> Referral | None:
        normalized_referral_id = self._normalize_uuid(
            referral_id,
            field_name="referral_id",
        )
        stmt = select(Referral).where(Referral.id == normalized_referral_id)
        return self.db.scalar(stmt)

    def list(
        self,
        *,
        organization_id: uuid.UUID | str | None = None,
        customer_account_id: uuid.UUID | str | None = None,
        search: str | None = None,
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[Referral], int]:
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
        normalized_search = self._normalize_optional_text(search)

        stmt = select(Referral)
        count_stmt: Select[tuple[int]] = select(func.count()).select_from(Referral)

        if normalized_organization_id is not None:
            stmt = stmt.where(Referral.organization_id == normalized_organization_id)
            count_stmt = count_stmt.where(Referral.organization_id == normalized_organization_id)

        if normalized_customer_account_id is not None:
            stmt = stmt.where(Referral.customer_account_id == normalized_customer_account_id)
            count_stmt = count_stmt.where(Referral.customer_account_id == normalized_customer_account_id)

        if normalized_search:
            pattern = f"%{normalized_search}%"
            search_filter = or_(
                Referral.referred_by_name.ilike(pattern),
                Referral.referred_by_phone.ilike(pattern),
                Referral.referred_by_email.ilike(pattern),
                Referral.notes.ilike(pattern),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        total = int(self.db.scalar(count_stmt) or 0)

        offset = (normalized_page - 1) * normalized_page_size
        stmt = (
            stmt.order_by(Referral.created_at.desc())
            .offset(offset)
            .limit(normalized_page_size)
        )

        items = list(self.db.scalars(stmt).all())
        return items, total

    def update(self, referral: Referral) -> Referral:
        self.db.add(referral)
        self.db.flush()
        self.db.refresh(referral)
        return referral

    def delete(self, referral: Referral) -> None:
        self.db.delete(referral)
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