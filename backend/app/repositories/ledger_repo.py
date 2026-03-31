from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.domain.models.ledger_entry import LedgerEntry


class LedgerRepository:
    DEFAULT_PAGE = 1
    DEFAULT_PAGE_SIZE = 100
    MAX_PAGE_SIZE = 500

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, ledger_entry: LedgerEntry) -> LedgerEntry:
        self.db.add(ledger_entry)
        self.db.flush()
        self.db.refresh(ledger_entry)
        return ledger_entry

    def create_many(self, ledger_entries: list[LedgerEntry]) -> list[LedgerEntry]:
        if not ledger_entries:
            return []

        self.db.add_all(ledger_entries)
        self.db.flush()

        for item in ledger_entries:
            self.db.refresh(item)

        return ledger_entries

    def get_by_id(self, ledger_entry_id: uuid.UUID) -> LedgerEntry | None:
        stmt = select(LedgerEntry).where(LedgerEntry.id == ledger_entry_id)
        return self.db.scalar(stmt)

    def list(
        self,
        *,
        organization_id: uuid.UUID | None = None,
        customer_account_id: uuid.UUID | None = None,
        billing_invoice_id: uuid.UUID | None = None,
        payment_id: uuid.UUID | None = None,
        entry_type: str | None = None,
        entry_date_from: date | None = None,
        entry_date_to: date | None = None,
        page: int = DEFAULT_PAGE,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[LedgerEntry], int]:
        normalized_page = max(page, 1)
        normalized_page_size = min(max(page_size, 1), self.MAX_PAGE_SIZE)

        stmt = select(LedgerEntry)
        count_stmt: Select[tuple[int]] = select(func.count()).select_from(LedgerEntry)

        if organization_id is not None:
            stmt = stmt.where(LedgerEntry.organization_id == organization_id)
            count_stmt = count_stmt.where(LedgerEntry.organization_id == organization_id)

        if customer_account_id is not None:
            stmt = stmt.where(LedgerEntry.customer_account_id == customer_account_id)
            count_stmt = count_stmt.where(
                LedgerEntry.customer_account_id == customer_account_id
            )

        if billing_invoice_id is not None:
            stmt = stmt.where(LedgerEntry.billing_invoice_id == billing_invoice_id)
            count_stmt = count_stmt.where(
                LedgerEntry.billing_invoice_id == billing_invoice_id
            )

        if payment_id is not None:
            stmt = stmt.where(LedgerEntry.payment_id == payment_id)
            count_stmt = count_stmt.where(LedgerEntry.payment_id == payment_id)

        if entry_type:
            stmt = stmt.where(LedgerEntry.entry_type == entry_type)
            count_stmt = count_stmt.where(LedgerEntry.entry_type == entry_type)

        if entry_date_from is not None:
            stmt = stmt.where(LedgerEntry.entry_date >= entry_date_from)
            count_stmt = count_stmt.where(LedgerEntry.entry_date >= entry_date_from)

        if entry_date_to is not None:
            stmt = stmt.where(LedgerEntry.entry_date <= entry_date_to)
            count_stmt = count_stmt.where(LedgerEntry.entry_date <= entry_date_to)

        total = self.db.scalar(count_stmt) or 0

        offset = (normalized_page - 1) * normalized_page_size
        stmt = (
            stmt.order_by(LedgerEntry.entry_date.desc(), LedgerEntry.created_at.desc())
            .offset(offset)
            .limit(normalized_page_size)
        )

        items = list(self.db.scalars(stmt).all())
        return items, total

    def update(self, ledger_entry: LedgerEntry) -> LedgerEntry:
        self.db.add(ledger_entry)
        self.db.flush()
        self.db.refresh(ledger_entry)
        return ledger_entry

    def delete(self, ledger_entry: LedgerEntry) -> None:
        self.db.delete(ledger_entry)
        self.db.flush()