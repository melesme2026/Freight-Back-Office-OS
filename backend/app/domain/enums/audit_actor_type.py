from __future__ import annotations

from app.domain.enums.compat import StrEnum


class AuditActorType(StrEnum):
    SYSTEM = "system"
    STAFF_USER = "staff_user"
    DRIVER = "driver"
    WEBHOOK = "webhook"