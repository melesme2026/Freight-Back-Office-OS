from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
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
        customer_account = self.customer_account_repo.get_by_id(customer_account_id)
        if customer_account is None:
            raise NotFoundError(
                "Customer account not found",
                details={"customer_account_id": customer_account_id},
            )

        existing = self.onboarding_repo.get_by_customer_account_id(customer_account_id)
        if existing is not None:
            return existing

        checklist = OnboardingChecklist(
            organization_id=organization_id,
            customer_account_id=customer_account_id,
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
        checklist = self.onboarding_repo.get_by_customer_account_id(customer_account_id)
        if checklist is None:
            raise NotFoundError(
                "Onboarding checklist not found",
                details={"customer_account_id": customer_account_id},
            )
        return checklist

    def upsert_checklist(
        self,
        *,
        organization_id: str,
        customer_account_id: str,
        status: str,
        documents_received: bool,
        pricing_confirmed: bool,
        payment_method_added: bool,
        driver_profiles_created: bool,
        channel_connected: bool,
        go_live_ready: bool,
        completed_at=None,
    ) -> OnboardingChecklist:
        checklist = self.onboarding_repo.get_by_customer_account_id(customer_account_id)

        if checklist is None:
            checklist = OnboardingChecklist(
                organization_id=organization_id,
                customer_account_id=customer_account_id,
                status=status,
                documents_received=documents_received,
                pricing_confirmed=pricing_confirmed,
                payment_method_added=payment_method_added,
                driver_profiles_created=driver_profiles_created,
                channel_connected=channel_connected,
                go_live_ready=go_live_ready,
                completed_at=completed_at,
            )
            return self.onboarding_repo.create(checklist)

        checklist.status = status
        checklist.documents_received = documents_received
        checklist.pricing_confirmed = pricing_confirmed
        checklist.payment_method_added = payment_method_added
        checklist.driver_profiles_created = driver_profiles_created
        checklist.channel_connected = channel_connected
        checklist.go_live_ready = go_live_ready
        checklist.completed_at = completed_at

        if go_live_ready and completed_at is None:
            checklist.completed_at = datetime.now(timezone.utc)

        if go_live_ready and str(checklist.status) != str(OnboardingStatus.COMPLETED):
            checklist.status = OnboardingStatus.COMPLETED

        return self.onboarding_repo.update(checklist)