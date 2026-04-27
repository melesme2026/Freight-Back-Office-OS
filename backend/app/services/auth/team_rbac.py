from __future__ import annotations

from app.core.exceptions import AppError
from app.domain.enums.compat import StrEnum
from app.domain.enums.role import Role


class TeamAction(StrEnum):
    DISABLE = "disable"
    ENABLE = "enable"
    REMOVE = "remove"


MANAGE_TEAM_ROLES = {Role.OWNER.value, Role.ADMIN.value}
OWNER_ADMIN_ROLES = {Role.OWNER.value, Role.ADMIN.value}


class TeamPermissionError(AppError):
    def __init__(self, message: str, *, code: str, details: dict[str, object] | None = None) -> None:
        super().__init__(message, code=code, status_code=403, details=details)


def normalize_role(value: object | None) -> str:
    enum_value = getattr(value, "value", value)
    return str(enum_value or "").strip().lower()


def can_manage_team(actor_role: object | None) -> bool:
    return normalize_role(actor_role) in MANAGE_TEAM_ROLES


def assert_can_manage_team(actor_role: object | None) -> None:
    if not can_manage_team(actor_role):
        raise TeamPermissionError(
            "You do not have permission to manage workspace team members.",
            code="forbidden_action",
        )


def can_modify_staff(actor_role: object | None, target_role: object | None, action: TeamAction) -> bool:
    actor = normalize_role(actor_role)
    target = normalize_role(target_role)

    if actor not in MANAGE_TEAM_ROLES:
        return False

    if actor == Role.OWNER.value:
        return target in {Role.ADMIN.value, Role.OPS_MANAGER.value, Role.OPS_AGENT.value, Role.BILLING_ADMIN.value, Role.SUPPORT_AGENT.value, Role.VIEWER.value}

    if actor == Role.ADMIN.value:
        return target in {Role.OPS_MANAGER.value, Role.OPS_AGENT.value, Role.BILLING_ADMIN.value, Role.SUPPORT_AGENT.value, Role.VIEWER.value}

    return False


def assert_can_modify_staff(actor_role: object | None, target_role: object | None, action: TeamAction) -> None:
    target = normalize_role(target_role)
    if target == Role.OWNER.value:
        raise TeamPermissionError(
            "Owners cannot be modified by this action.",
            code="cannot_modify_owner",
        )

    if not can_modify_staff(actor_role, target_role, action):
        raise TeamPermissionError(
            "You are not allowed to perform this action for the selected team member.",
            code="forbidden_action",
            details={
                "action": action.value,
                "actor_role": normalize_role(actor_role),
                "target_role": target,
            },
        )
