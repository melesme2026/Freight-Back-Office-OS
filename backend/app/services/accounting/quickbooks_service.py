from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class QuickBooksExportInvoice:
    doc_number: str
    customer_name: str
    line_description: str
    amount: Decimal
    txn_date: str | None
    private_note: str | None


class QuickBooksIntegrationService:
    """Export-ready QuickBooks boundary.

    PR-38 intentionally does not store OAuth secrets or run bidirectional sync.
    This service owns the shape of safe future QuickBooks payloads while CSV
    exports remain the production path until credentials and review controls are
    configured.
    """

    provider = "quickbooks"
    sync_mode = "export_ready"

    def format_invoice_payload(self, row: dict[str, str]) -> QuickBooksExportInvoice:
        return QuickBooksExportInvoice(
            doc_number=row.get("invoice_number") or row.get("load_number") or "",
            customer_name=row.get("broker_customer") or "Unknown customer",
            line_description=f"Freight load {row.get('load_number') or ''}".strip(),
            amount=Decimal(row.get("gross_amount") or "0"),
            txn_date=row.get("invoice_date") or None,
            private_note=row.get("notes") or None,
        )

    def capability_summary(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "sync_mode": self.sync_mode,
            "supports_csv_exports": True,
            "supports_direct_push": False,
            "notes": (
                "QuickBooks payload formatting is available, but OAuth/token storage "
                "and direct sync are intentionally not enabled in PR-38."
            ),
        }
