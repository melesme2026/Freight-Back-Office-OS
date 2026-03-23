from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.models.ledger_entry import LedgerEntry
from app.repositories.ledger_repo import LedgerRepository


class LedgerService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.ledger_repo = LedgerRepository(db)

    def create_entry(
        self,
        *,
        organization_id: str,
        entry_type: str,
        amount: Decimal,
        description: str,
        entry_date: date,
        customer_account_id: str | None = None,
        billing_invoice_id: str | None = None,
        payment_id: str | None = None,
        currency_code: str = "USD",
        metadata_json: dict | list | None = None,
    ) -> LedgerEntry:
        entry = LedgerEntry(
            organization_id=organization_id,
            customer_account_id=customer_account_id,
            billing_invoice_id=billing_invoice_id,
            payment_id=payment_id,
            entry_type=entry_type,
            amount=amount,
            currency_code=currency_code,
            description=description,
            entry_date=entry_date,
            metadata_json=metadata_json,
        )
        return self.ledger_repo.create(entry)

    def list_entries(
        self,
        *,
        organization_id: str | None = None,
        customer_account_id: str | None = None,
        billing_invoice_id: str | None = None,
        payment_id: str | None = None,
        entry_type: str | None = None,
        entry_date_from: date | None = None,
        entry_date_to: date | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> tuple[list[LedgerEntry], int]:
        return self.ledger_repo.list(
            organization_id=organization_id,
            customer_account_id=customer_account_id,
            billing_invoice_id=billing_invoice_id,
            payment_id=payment_id,
            entry_type=entry_type,
            entry_date_from=entry_date_from,
            entry_date_to=entry_date_to,
            page=page,
            page_size=page_size,
        )