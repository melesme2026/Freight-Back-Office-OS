from __future__ import annotations

from app.domain.enums.compat import StrEnum


class ValidationSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"