from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
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
            organization_id=self._require_text(
                organization_id,
                field_name="organization_id",
            ),
            customer_account_id=self._clean_text(customer_account_id),
            referred_by_name=self._require_text(
                referred_by_name,
                field_name="referred_by_name",
            ),
            referred_by_phone=self._clean_text(referred_by_phone),
            referred_by_email=self._normalize_email(referred_by_email),
            notes=self._clean_text(notes),
        )
        created = self.referral_repo.create(referral)
        return self.referral_repo.get_by_id(created.id) or created

    def get_referral(self, referral_id: str) -> Referral:
        normalized_referral_id = self._require_text(
            referral_id,
            field_name="referral_id",
        )
        referral = self.referral_repo.get_by_id(normalized_referral_id)
        if referral is None:
            raise NotFoundError(
                "Referral not found",
                details={"referral_id": normalized_referral_id},
            )
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
            organization_id=self._clean_text(organization_id),
            customer_account_id=self._clean_text(customer_account_id),
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
            if not hasattr(referral, field):
                continue

            if field == "referred_by_name":
                if value is None:
                    continue
                setattr(
                    referral,
                    field,
                    self._require_text(value, field_name="referred_by_name"),
                )
                continue

            if field in {"referred_by_phone", "notes"}:
                setattr(referral, field, self._clean_text(value))
                continue

            if field == "referred_by_email":
                setattr(referral, field, self._normalize_email(value))
                continue

            if value is not None:
                setattr(referral, field, value)

        updated = self.referral_repo.update(referral)
        return self.referral_repo.get_by_id(updated.id) or updated

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

    def _require_text(self, value: str | None, *, field_name: str) -> str:
        cleaned = self._clean_text(value)
        if not cleaned:
            raise ValidationError(
                f"{field_name} is required",
                details={field_name: value},
            )
        return cleaned