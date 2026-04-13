from __future__ import annotations

from app.domain.enums.compat import StrEnum


class Role(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    OPS_MANAGER = "ops_manager"
    OPS_AGENT = "ops_agent"
    DRIVER = "driver"
    BILLING_ADMIN = "billing_admin"
    SUPPORT_AGENT = "support_agent"
    VIEWER = "viewer"
