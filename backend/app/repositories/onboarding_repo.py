from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models.onboarding_checklist import OnboardingChecklist


class OnboardingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, checklist: OnboardingChecklist) -> OnboardingChecklist:
        self.db.add(checklist)
        self.db.flush()
        self.db.refresh(checklist)
        return checklist

    def get_by_id(
        self,
        checklist_id: uuid.UUID | str,
    ) -> OnboardingChecklist | None:
        normalized_checklist_id = self._normalize_uuid(
            checklist_id,
            field_name="checklist_id",
        )
        stmt = select(OnboardingChecklist).where(
            OnboardingChecklist.id == normalized_checklist_id
        )
        return self.db.scalar(stmt)

    def get_by_customer_account_id(
        self,
        customer_account_id: uuid.UUID | str,
    ) -> OnboardingChecklist | None:
        normalized_customer_account_id = self._normalize_uuid(
            customer_account_id,
            field_name="customer_account_id",
        )
        stmt = select(OnboardingChecklist).where(
            OnboardingChecklist.customer_account_id == normalized_customer_account_id
        )
        return self.db.scalar(stmt)

    def update(self, checklist: OnboardingChecklist) -> OnboardingChecklist:
        self.db.add(checklist)
        self.db.flush()
        self.db.refresh(checklist)
        return checklist

    def delete(self, checklist: OnboardingChecklist) -> None:
        self.db.delete(checklist)
        self.db.flush()

    def _normalize_uuid(self, value: uuid.UUID | str, *, field_name: str) -> uuid.UUID:
        if isinstance(value, uuid.UUID):
            return value

        try:
            return uuid.UUID(str(value))
        except ValueError as exc:
            raise ValueError(f"Invalid {field_name}: {value}") from exc