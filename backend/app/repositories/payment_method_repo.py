from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select, update
from sqlalchemy.orm import Session

from app.domain.enums.payment_provider import PaymentProvider
from app.domain.models.payment_method import PaymentMethod


class PaymentMethodRepository:
    DEFAULT_PAGE = 1
    DEFAULT_PAGE_SIZE = 50
    MAX_PAGE_SIZE = 500

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payment_method: PaymentMethod) -> PaymentMethod:
        self.db.add(payment_method)
        self.db.flush()
        self.db.refresh(payment_method)
        return payment_method

    def get_by_id(
        self,
        payment_method_id: uuid.UUID | str,
    ) -> PaymentMethod | None:
        normalized_id = self._normalize_uuid(payment_method_id, field_name="payment_method_id")
        stmt = select(PaymentMethod).where(PaymentMethod.id == normalized_id)
        return self.db.scalar(stmt)

    def get_by_provider_payment_method_id(
        self,
        *,
        customer_account_id: uuid.UUID | str,
        provider_payment_method_id: str,
    ) -> PaymentMethod | None:
        normalized_customer_account_id = self._normalize_uuid(
            customer_account_id,
            field_name="customer_account_id",
        )

        stmt = select(PaymentMethod).where(
            PaymentMethod.customer_account_id == normalized_customer_account_id,
            PaymentMethod.provider_payment_method_id == provider_payment_method_id,
        )
        return self.db.scalar(stmt)

    def get_default_for_customer_account(
        self,
        customer_account_id: uuid.UUID | str,
    ) -> PaymentMethod | None:
        normalized_customer_account_id = self._normalize_uuid(
            customer_account_id,
            field_name="customer_account_id",
        )

        stmt = select(PaymentMethod).where(
            PaymentMethod.customer_account_id == normalized_customer_account_id,
            PaymentMethod.is_default.is_(True),
            PaymentMethod.is_active.is_(True),
        )
        return self.db.scalar(stmt)

    def list(
        self,
        *,
        organization_id: uuid.UUID | str | None = None,
        customer_account_id: uuid.UUID | str | None = None,
        provider: PaymentProvider | str | None = None,
        is_default: bool | None = None,
        is_active: bool | None = None,
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[PaymentMethod], int]:
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
        normalized_provider = self._normalize_provider(provider)

        stmt = select(PaymentMethod)
        count_stmt: Select[tuple[int]] = select(func.count()).select_from(PaymentMethod)

        if normalized_organization_id is not None:
            stmt = stmt.where(PaymentMethod.organization_id == normalized_organization_id)
            count_stmt = count_stmt.where(PaymentMethod.organization_id == normalized_organization_id)

        if normalized_customer_account_id is not None:
            stmt = stmt.where(PaymentMethod.customer_account_id == normalized_customer_account_id)
            count_stmt = count_stmt.where(
                PaymentMethod.customer_account_id == normalized_customer_account_id
            )

        if normalized_provider is not None:
            stmt = stmt.where(PaymentMethod.provider == normalized_provider)
            count_stmt = count_stmt.where(PaymentMethod.provider == normalized_provider)

        if is_default is not None:
            stmt = stmt.where(PaymentMethod.is_default == is_default)
            count_stmt = count_stmt.where(PaymentMethod.is_default == is_default)

        if is_active is not None:
            stmt = stmt.where(PaymentMethod.is_active == is_active)
            count_stmt = count_stmt.where(PaymentMethod.is_active == is_active)

        total = int(self.db.scalar(count_stmt) or 0)

        offset = (normalized_page - 1) * normalized_page_size
        stmt = (
            stmt.order_by(
                PaymentMethod.is_default.desc(),
                PaymentMethod.created_at.desc(),
            )
            .offset(offset)
            .limit(normalized_page_size)
        )

        items = list(self.db.scalars(stmt).all())
        return items, total

    def clear_default_for_customer_account(
        self,
        customer_account_id: uuid.UUID | str,
    ) -> int:
        normalized_customer_account_id = self._normalize_uuid(
            customer_account_id,
            field_name="customer_account_id",
        )

        stmt = (
            update(PaymentMethod)
            .where(
                PaymentMethod.customer_account_id == normalized_customer_account_id,
                PaymentMethod.is_default.is_(True),
            )
            .values(is_default=False)
        )

        result = self.db.execute(stmt)
        self.db.flush()

        return result.rowcount or 0

    def update(self, payment_method: PaymentMethod) -> PaymentMethod:
        self.db.add(payment_method)
        self.db.flush()
        self.db.refresh(payment_method)
        return payment_method

    def delete(self, payment_method: PaymentMethod) -> None:
        self.db.delete(payment_method)
        self.db.flush()

    def _normalize_uuid(self, value: uuid.UUID | str, *, field_name: str) -> uuid.UUID:
        if isinstance(value, uuid.UUID):
            return value

        try:
            return uuid.UUID(str(value))
        except ValueError as exc:
            raise ValueError(f"Invalid {field_name}: {value}") from exc

    def _normalize_provider(
        self,
        value: PaymentProvider | str | None,
    ) -> PaymentProvider | None:
        if value is None:
            return None

        if isinstance(value, PaymentProvider):
            return value

        normalized = str(value).strip().lower()

        for provider in PaymentProvider:
            if normalized == provider.value.lower():
                return provider
            if normalized == provider.name.lower():
                return provider

        raise ValueError(f"Invalid provider: {value}")