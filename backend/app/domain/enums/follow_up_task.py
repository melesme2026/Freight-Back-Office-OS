from __future__ import annotations

from app.domain.enums.compat import StrEnum


class FollowUpTaskType(StrEnum):
    PACKET_FOLLOW_UP = "packet_follow_up"
    PAYMENT_OVERDUE = "payment_overdue"
    RESERVE_FOLLOW_UP = "reserve_follow_up"
    PARTIAL_PAYMENT_FOLLOW_UP = "partial_payment_follow_up"
    SHORT_PAY_FOLLOW_UP = "short_pay_follow_up"
    DISPUTE_FOLLOW_UP = "dispute_follow_up"
    MANUAL_FOLLOW_UP = "manual_follow_up"


class FollowUpTaskStatus(StrEnum):
    OPEN = "open"
    SNOOZED = "snoozed"
    COMPLETED = "completed"
    CANCELED = "canceled"


class FollowUpTaskPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
