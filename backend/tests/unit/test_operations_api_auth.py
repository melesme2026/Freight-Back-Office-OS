from __future__ import annotations

import pytest

from app.api.v1.operations import _require_admin, _require_command_center_access
from app.core.exceptions import ForbiddenError


def test_driver_is_blocked_from_command_center() -> None:
    with pytest.raises(ForbiddenError):
        _require_command_center_access({"role": "driver"})


def test_staff_roles_are_allowed_for_command_center() -> None:
    for role in ["owner", "admin", "ops_manager", "ops_agent", "billing_admin", "support_agent"]:
        _require_command_center_access({"role": role})


def test_legacy_support_label_is_denied_for_command_center() -> None:
    with pytest.raises(ForbiddenError):
        _require_command_center_access({"role": "support"})


def test_storage_cleanup_requires_admin_owner_or_ops_manager_support_agent() -> None:
    for role in ["owner", "admin", "ops_manager", "support_agent"]:
        _require_admin({"role": role})
    with pytest.raises(ForbiddenError):
        _require_admin({"role": "ops_agent"})
