from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.domain.models.referral import Referral
from app.repositories.referral_repo import ReferralRepository


class ReferralService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.referral_repo = ReferralRepository(db)

    def create_referral(
        self,
        *,
        organization_id: str,
        referred_by_name: str,
        customer_account_id: str | None = None,
        referred_by_phone: str | None = None,
        referred_by_email: str | None = None,
        notes: str | None = None,
    ) -> Referral:
        referral = Referral(
            organization_id=organization_id,
            customer_account_id=customer_account_id,
            referred_by_name=self._clean_text(referred_by_name),
            referred_by_phone=self._clean_text(referred_by_phone),
            referred_by_email=self._normalize_email(referred_by_email),
            notes=self._clean_text(notes),
        )
        return self.referral_repo.create(referral)

    def get_referral(self, referral_id: str) -> Referral:
        referral = self.referral_repo.get_by_id(referral_id)
        if referral is None:
            raise NotFoundError("Referral not found", details={"referral_id": referral_id})
        return referral

    def list_referrals(
        self,
        *,
        organization_id: str | None = None,
        customer_account_id: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[Referral], int]:
        return self.referral_repo.list(
            organization_id=organization_id,
            customer_account_id=customer_account_id,
            search=self._clean_text(search),
            page=page,
            page_size=page_size,
        )

    def update_referral(
        self,
        *,
        referral_id: str,
        **updates,
    ) -> Referral:
        referral = self.get_referral(referral_id)

        for field, value in updates.items():
            if not hasattr(referral, field) or value is None:
                continue

            if field in {"referred_by_name", "referred_by_phone", "notes"}:
                setattr(referral, field, self._clean_text(value))
            elif field == "referred_by_email":
                setattr(referral, field, self._normalize_email(value))
            else:
                setattr(referral, field, value)

        return self.referral_repo.update(referral)

    @staticmethod
    def _clean_text(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    @staticmethod
    def _normalize_email(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip().lower()
        return cleaned or None