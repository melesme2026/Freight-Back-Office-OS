from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import DuplicateRecordError, NotFoundError
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
        normalized_account_code = self._clean_text(account_code)

        if normalized_account_code:
            existing = self.customer_account_repo.get_by_account_code(normalized_account_code)
            if existing is not None:
                raise DuplicateRecordError(
                    "Customer account code already exists",
                    details={"account_code": normalized_account_code},
                )

        customer_account = CustomerAccount(
            organization_id=organization_id,
            account_name=self._clean_text(account_name),
            account_code=normalized_account_code,
            status=CustomerAccountStatus.PROSPECT,
            primary_contact_name=self._clean_text(primary_contact_name),
            primary_contact_email=self._normalize_email(primary_contact_email),
            primary_contact_phone=self._clean_text(primary_contact_phone),
            billing_email=self._normalize_email(billing_email),
            notes=self._clean_text(notes),
        )
        return self.customer_account_repo.create(customer_account)

    def get_customer_account(self, customer_account_id: str) -> CustomerAccount:
        customer_account = self.customer_account_repo.get_by_id(customer_account_id)
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
        return self.customer_account_repo.list(
            organization_id=organization_id,
            status=status,
            search=self._clean_text(search),
            page=page,
            page_size=page_size,
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
                if existing is not None and str(existing.id) != str(customer_account.id):
                    raise DuplicateRecordError(
                        "Customer account code already exists",
                        details={"account_code": new_account_code},
                    )
                updates["account_code"] = new_account_code

        for field, value in updates.items():
            if not hasattr(customer_account, field) or value is None:
                continue

            if field in {"account_name", "primary_contact_name", "primary_contact_phone", "notes"}:
                setattr(customer_account, field, self._clean_text(value))
            elif field in {"primary_contact_email", "billing_email"}:
                setattr(customer_account, field, self._normalize_email(value))
            else:
                setattr(customer_account, field, value)

        return self.customer_account_repo.update(customer_account)

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