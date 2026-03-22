from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    OPS_MANAGER = "ops_manager"
    OPS_AGENT = "ops_agent"
    BILLING_ADMIN = "billing_admin"
    SUPPORT_AGENT = "support_agent"
    VIEWER = "viewer"