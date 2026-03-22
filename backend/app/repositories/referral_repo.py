from __future__ import annotations

import uuid

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.domain.models.referral import Referral


class ReferralRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, referral: Referral) -> Referral:
        self.db.add(referral)
        self.db.flush()
        self.db.refresh(referral)
        return referral

    def get_by_id(self, referral_id: uuid.UUID) -> Referral | None:
        stmt = select(Referral).where(Referral.id == referral_id)
        return self.db.scalar(stmt)

    def list(
        self,
        *,
        organization_id: uuid.UUID | None = None,
        customer_account_id: uuid.UUID | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[Referral], int]:
        stmt = select(Referral)
        count_stmt: Select[tuple[int]] = select(func.count()).select_from(Referral)

        if organization_id is not None:
            stmt = stmt.where(Referral.organization_id == organization_id)
            count_stmt = count_stmt.where(Referral.organization_id == organization_id)

        if customer_account_id is not None:
            stmt = stmt.where(Referral.customer_account_id == customer_account_id)
            count_stmt = count_stmt.where(Referral.customer_account_id == customer_account_id)

        if search:
            pattern = f"%{search.strip()}%"
            search_filter = or_(
                Referral.referred_by_name.ilike(pattern),
                Referral.referred_by_phone.ilike(pattern),
                Referral.referred_by_email.ilike(pattern),
                Referral.notes.ilike(pattern),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        total = self.db.scalar(count_stmt) or 0

        offset = max(page - 1, 0) * page_size
        stmt = stmt.order_by(Referral.created_at.desc()).offset(offset).limit(page_size)

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