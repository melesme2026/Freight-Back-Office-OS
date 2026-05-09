from __future__ import annotations

import uuid
from typing import Any

from app.core.exceptions import UnauthorizedError, ValidationError
from app.domain.models.audit_log import AuditLog
from app.services.audit.audit_service import AuditService
from sqlalchemy.orm import Session

SAFE_METADATA_KEYS = {
    "document_type",
    "filename",
    "file_size_bytes",
    "load_id",
    "load_number",
    "status",
    "previous_status",
    "row_count",
    "export_kind",
    "warning",
    "quota",
    "usage",
}


class ActivityService:
    DEFAULT_LIMIT = 25
    MAX_LIMIT = 100

    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit_service = AuditService(db)

    def list_recent_activity(
        self,
        *,
        organization_id: str,
        token_payload: dict[str, Any],
        limit: int = DEFAULT_LIMIT,
        entity_type: str | None = None,
        action: str | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        token_org_id = token_payload.get("organization_id")
        if not token_org_id or str(token_org_id) != str(organization_id):
            raise UnauthorizedError(
                "Activity can only be viewed for the authenticated organization"
            )

        normalized_limit = min(max(int(limit or self.DEFAULT_LIMIT), 1), self.MAX_LIMIT)
        items, total = self.audit_service.list_audit_logs(
            organization_id=organization_id,
            entity_type=entity_type,
            action=action,
            page=1,
            page_size=normalized_limit,
        )
        return [self.serialize(log) for log in items], {
            "total_count": total,
            "limit": normalized_limit,
            "organization_id": str(organization_id),
        }

    @staticmethod
    def serialize(log: AuditLog) -> dict[str, Any]:
        metadata = log.metadata_json if isinstance(log.metadata_json, dict) else {}
        safe_metadata = {
            key: value
            for key, value in metadata.items()
            if key in SAFE_METADATA_KEYS and not ActivityService._looks_sensitive(key, value)
        }
        return {
            "id": str(log.id),
            "organization_id": str(log.organization_id),
            "actor_type": getattr(log.actor_type, "value", str(log.actor_type)),
            "actor_id": str(log.actor_id) if log.actor_id else None,
            "entity_type": log.entity_type,
            "entity_id": str(log.entity_id),
            "action": log.action,
            "metadata": safe_metadata,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }

    @staticmethod
    def _looks_sensitive(key: str, value: Any) -> bool:
        lowered = key.lower()
        if any(marker in lowered for marker in ("secret", "token", "password", "card", "stripe")):
            return True
        if isinstance(value, str) and len(value) > 500:
            return True
        return False


def organization_id_from_token(token_payload: dict[str, Any]) -> str:
    org_id = token_payload.get("organization_id")
    if not org_id:
        raise UnauthorizedError("Missing organization context")
    try:
        return str(uuid.UUID(str(org_id)))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValidationError(
            "Invalid organization context", details={"organization_id": org_id}
        ) from exc
