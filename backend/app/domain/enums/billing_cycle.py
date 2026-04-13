from __future__ import annotations

from app.domain.enums.compat import StrEnum


class BillingCycle(StrEnum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    CUSTOM = "custom"