from __future__ import annotations

from app.domain.enums.compat import StrEnum


class LoadStatus(StrEnum):
    BOOKED = "booked"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    DOCS_RECEIVED = "docs_received"
    DOCS_NEEDS_ATTENTION = "docs_needs_attention"
    INVOICE_READY = "invoice_ready"
    SUBMITTED_TO_BROKER = "submitted_to_broker"
    SUBMITTED_TO_FACTORING = "submitted_to_factoring"
    PACKET_REJECTED = "packet_rejected"
    RESUBMISSION_NEEDED = "resubmission_needed"
    ADVANCE_PAID = "advance_paid"
    RESERVE_PENDING = "reserve_pending"
    FULLY_PAID = "fully_paid"
    SHORT_PAID = "short_paid"
    DISPUTED = "disputed"
    ARCHIVED = "archived"
