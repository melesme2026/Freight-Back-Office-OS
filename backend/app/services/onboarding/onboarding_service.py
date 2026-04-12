from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.domain.enums.onboarding_status import OnboardingStatus
from app.domain.models.onboarding_checklist import OnboardingChecklist
from app.repositories.customer_account_repo import CustomerAccountRepository
from app.repositories.onboarding_repo import OnboardingRepository


class OnboardingService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.onboarding_repo = OnboardingRepository(db)
        self.customer_account_repo = CustomerAccountRepository(db)

    def create_or_initialize_checklist(
        self,
        *,
        organization_id: str,
        customer_account_id: str,
    ) -> OnboardingChecklist:
        normalized_organization_id = self._require_text(
            organization_id,
            field_name="organization_id",
        )
        normalized_customer_account_id = self._require_text(
            customer_account_id,
            field_name="customer_account_id",
        )

        customer_account = self.customer_account_repo.get_by_id(normalized_customer_account_id)
        if customer_account is None:
            raise NotFoundError(
                "Customer account not found",
                details={"customer_account_id": normalized_customer_account_id},
            )

        if str(customer_account.organization_id) != normalized_organization_id:
            raise ValidationError(
                "Customer account does not belong to the provided organization",
                details={
                    "organization_id": normalized_organization_id,
                    "customer_account_id": normalized_customer_account_id,
                },
            )

        existing = self.onboarding_repo.get_by_customer_account_id(normalized_customer_account_id)
        if existing is not None:
            return existing

        checklist = OnboardingChecklist(
            organization_id=normalized_organization_id,
            customer_account_id=normalized_customer_account_id,
            status=OnboardingStatus.NOT_STARTED,
            documents_received=False,
            pricing_confirmed=False,
            payment_method_added=False,
            driver_profiles_created=False,
            channel_connected=False,
            go_live_ready=False,
            completed_at=None,
        )
        return self.onboarding_repo.create(checklist)

    def get_checklist(self, customer_account_id: str) -> OnboardingChecklist:
        normalized_customer_account_id = self._require_text(
            customer_account_id,
            field_name="customer_account_id",
        )

        checklist = self.onboarding_repo.get_by_customer_account_id(normalized_customer_account_id)
        if checklist is None:
            raise NotFoundError(
                "Onboarding checklist not found",
                details={"customer_account_id": normalized_customer_account_id},
            )
        return checklist

    def upsert_checklist(
        self,
        *,
        organization_id: str,
        customer_account_id: str,
        status: str | OnboardingStatus,
        documents_received: bool,
        pricing_confirmed: bool,
        payment_method_added: bool,
        driver_profiles_created: bool,
        channel_connected: bool,
        go_live_ready: bool,
        completed_at: Any = None,
    ) -> OnboardingChecklist:
        normalized_organization_id = self._require_text(
            organization_id,
            field_name="organization_id",
        )
        normalized_customer_account_id = self._require_text(
            customer_account_id,
            field_name="customer_account_id",
        )

        customer_account = self.customer_account_repo.get_by_id(normalized_customer_account_id)
        if customer_account is None:
            raise NotFoundError(
                "Customer account not found",
                details={"customer_account_id": normalized_customer_account_id},
            )

        if str(customer_account.organization_id) != normalized_organization_id:
            raise ValidationError(
                "Customer account does not belong to the provided organization",
                details={
                    "organization_id": normalized_organization_id,
                    "customer_account_id": normalized_customer_account_id,
                },
            )

        normalized_status = self._normalize_status(status)
        normalized_completed_at = self._normalize_datetime(
            completed_at,
            field_name="completed_at",
            allow_none=True,
        )

        checklist = self.onboarding_repo.get_by_customer_account_id(normalized_customer_account_id)

        if go_live_ready and normalized_completed_at is None:
            normalized_completed_at = datetime.now(timezone.utc)

        if go_live_ready and normalized_status != OnboardingStatus.COMPLETED:
            normalized_status = OnboardingStatus.COMPLETED

        if checklist is None:
            checklist = OnboardingChecklist(
                organization_id=normalized_organization_id,
                customer_account_id=normalized_customer_account_id,
                status=normalized_status,
                documents_received=documents_received,
                pricing_confirmed=pricing_confirmed,
                payment_method_added=payment_method_added,
                driver_profiles_created=driver_profiles_created,
                channel_connected=channel_connected,
                go_live_ready=go_live_ready,
                completed_at=normalized_completed_at,
            )
            return self.onboarding_repo.create(checklist)

        checklist.status = normalized_status
        checklist.documents_received = documents_received
        checklist.pricing_confirmed = pricing_confirmed
        checklist.payment_method_added = payment_method_added
        checklist.driver_profiles_created = driver_profiles_created
        checklist.channel_connected = channel_connected
        checklist.go_live_ready = go_live_ready
        checklist.completed_at = normalized_completed_at

        return self.onboarding_repo.update(checklist)

    def _normalize_status(self, value: str | OnboardingStatus) -> OnboardingStatus:
        if isinstance(value, OnboardingStatus):
            return value

        normalized = str(value).strip().lower()

        aliases: dict[str, OnboardingStatus] = {
            "not_started": OnboardingStatus.NOT_STARTED,
            "not started": OnboardingStatus.NOT_STARTED,
            "in_progress": OnboardingStatus.IN_PROGRESS,
            "in progress": OnboardingStatus.IN_PROGRESS,
            "completed": OnboardingStatus.COMPLETED,
            "blocked": OnboardingStatus.BLOCKED,
        }

        if normalized in aliases:
            return aliases[normalized]

        raise ValidationError(
            "Invalid onboarding status",
            details={"status": value},
        )

    @staticmethod
    def _normalize_datetime(
        value: Any,
        *,
        field_name: str,
        allow_none: bool = False,
    ) -> datetime | None:
        if value is None or value == "":
            if allow_none:
                return None
            raise ValidationError(
                f"{field_name} is required",
                details={field_name: value},
            )

        if isinstance(value, datetime):
            return value

        try:
            return datetime.fromisoformat(str(value).strip())
        except ValueError as exc:
            raise ValidationError(
                f"Invalid {field_name}",
                details={field_name: value},
            ) from exc

    @staticmethod
    def _require_text(value: str | None, *, field_name: str) -> str:
        normalized = str(value).strip() if value is not None else ""
        if not normalized:
            raise ValidationError(
                f"{field_name} is required",
                details={field_name: value},
            )
        return normalized