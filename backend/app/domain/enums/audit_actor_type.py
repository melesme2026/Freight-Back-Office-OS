from __future__ import annotations

from enum import StrEnum


class AuditActorType(StrEnum):
    SYSTEM = "system"
    STAFF_USER = "staff_user"
    DRIVER = "driver"
    WEBHOOK = "webhook"