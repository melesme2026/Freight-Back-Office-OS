from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import DuplicateRecordError, NotFoundError, ValidationError
from app.domain.enums.customer_account_status import CustomerAccountStatus
from app.domain.models.customer_account import CustomerAccount
from app.repositories.customer_account_repo import CustomerAccountRepository


class CustomerAccountService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.customer_account_repo = CustomerAccountRepository(db)

    def create_customer_account(
        self,
        *,
        organization_id: str,
        account_name: str,
        account_code: str | None = None,
        primary_contact_name: str | None = None,
        primary_contact_email: str | None = None,
        primary_contact_phone: str | None = None,
        billing_email: str | None = None,
        notes: str | None = None,
    ) -> CustomerAccount:
        normalized_organization_id = self._require_text(
            organization_id,
            field_name="organization_id",
        )
        normalized_account_name = self._require_text(account_name, field_name="account_name")
        normalized_account_code = self._clean_text(account_code)

        if normalized_account_code:
            existing = self.customer_account_repo.get_by_account_code(normalized_account_code)
            if (
                existing is not None
                and str(existing.organization_id) == normalized_organization_id
            ):
                raise DuplicateRecordError(
                    "Customer account code already exists",
                    details={
                        "organization_id": normalized_organization_id,
                        "account_code": normalized_account_code,
                    },
                )

        customer_account = CustomerAccount(
            organization_id=normalized_organization_id,
            account_name=normalized_account_name,
            account_code=normalized_account_code,
            status=CustomerAccountStatus.PROSPECT,
            primary_contact_name=self._clean_text(primary_contact_name),
            primary_contact_email=self._normalize_email(primary_contact_email),
            primary_contact_phone=self._clean_text(primary_contact_phone),
            billing_email=self._normalize_email(billing_email),
            notes=self._clean_text(notes),
        )
        created = self.customer_account_repo.create(customer_account)
        return (
            self.customer_account_repo.get_by_id(created.id, include_related=True) or created
        )

    def get_customer_account(self, customer_account_id: str) -> CustomerAccount:
        customer_account = self.customer_account_repo.get_by_id(
            customer_account_id,
            include_related=True,
        )
        if customer_account is None:
            raise NotFoundError(
                "Customer account not found",
                details={"customer_account_id": customer_account_id},
            )
        return customer_account

    def list_customer_accounts(
        self,
        *,
        organization_id: str | None = None,
        status: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[CustomerAccount], int]:
        normalized_status = self._normalize_status(status)

        return self.customer_account_repo.list(
            organization_id=self._clean_text(organization_id),
            status=normalized_status,
            search=self._clean_text(search),
            page=page,
            page_size=page_size,
            include_related=True,
        )

    def update_customer_account(
        self,
        *,
        customer_account_id: str,
        **updates,
    ) -> CustomerAccount:
        customer_account = self.get_customer_account(customer_account_id)

        if "account_code" in updates:
            new_account_code = self._clean_text(updates.get("account_code"))
            if new_account_code and new_account_code != customer_account.account_code:
                existing = self.customer_account_repo.get_by_account_code(new_account_code)
                if (
                    existing is not None
                    and str(existing.id) != str(customer_account.id)
                    and str(existing.organization_id) == str(customer_account.organization_id)
                ):
                    raise DuplicateRecordError(
                        "Customer account code already exists",
                        details={
                            "organization_id": str(customer_account.organization_id),
                            "account_code": new_account_code,
                        },
                    )
            updates["account_code"] = new_account_code

        if "status" in updates:
            updates["status"] = self._normalize_status(updates.get("status"))

        text_fields = {"primary_contact_name", "primary_contact_phone", "notes"}
        email_fields = {"primary_contact_email", "billing_email"}

        for field, value in updates.items():
            if not hasattr(customer_account, field):
                continue

            if field == "account_name":
                if value is None:
                    continue
                setattr(
                    customer_account,
                    field,
                    self._require_text(value, field_name="account_name"),
                )
                continue

            if field in text_fields:
                setattr(customer_account, field, self._clean_text(value))
                continue

            if field in email_fields:
                setattr(customer_account, field, self._normalize_email(value))
                continue

            setattr(customer_account, field, value)

        updated = self.customer_account_repo.update(customer_account)
        return (
            self.customer_account_repo.get_by_id(updated.id, include_related=True) or updated
        )

    @staticmethod
    def _clean_text(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    @staticmethod
    def _require_text(value: str | None, *, field_name: str) -> str:
        cleaned = CustomerAccountService._clean_text(value)
        if not cleaned:
            raise ValidationError(
                f"{field_name.replace('_', ' ').capitalize()} is required.",
                details={field_name: "This field cannot be blank."},
            )
        return cleaned

    @staticmethod
    def _normalize_email(value: str | None) -> str | None:
        cleaned = CustomerAccountService._clean_text(value)
        return cleaned.lower() if cleaned else None

    @staticmethod
    def _normalize_status(
        value: str | CustomerAccountStatus | None,
    ) -> CustomerAccountStatus | None:
        if value is None:
            return None

        if isinstance(value, CustomerAccountStatus):
            return value

        normalized = str(value).strip().lower()
        if not normalized:
            return None

        for member in CustomerAccountStatus:
            if member.value == normalized:
                return member
            if member.name.lower() == normalized:
                return member

        raise ValidationError(
            "Invalid customer account status.",
            details={"status": normalized},
        )