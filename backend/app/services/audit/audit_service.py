from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.domain.models.audit_log import AuditLog
from app.repositories.audit_repo import AuditRepository


class AuditService:
    DEFAULT_PAGE = 1
    DEFAULT_PAGE_SIZE = 100
    MAX_PAGE_SIZE = 500

    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit_repo = AuditRepository(db)

    @staticmethod
    def _parse_uuid(
        value: str | None,
        *,
        field_name: str,
        error_message: str,
    ) -> uuid.UUID | None:
        if value is None:
            return None
        try:
            return uuid.UUID(str(value))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValidationError(
                error_message,
                details={field_name: value},
            ) from exc

    @classmethod
    def _normalize_page(cls, page: int) -> int:
        return max(cls.DEFAULT_PAGE, page)

    @classmethod
    def _normalize_page_size(cls, page_size: int) -> int:
        if page_size < 1:
            return cls.DEFAULT_PAGE_SIZE
        return min(page_size, cls.MAX_PAGE_SIZE)

    def log_event(
        self,
        *,
        organization_id: str,
        entity_type: str,
        entity_id: str,
        action: str,
        actor_id: str | None = None,
        actor_type: str = "system",
        changes_json: dict[str, Any] | list[Any] | None = None,
        metadata_json: dict[str, Any] | list[Any] | None = None,
    ) -> AuditLog:
        parsed_organization_id = self._parse_uuid(
            organization_id,
            field_name="organization_id",
            error_message="Invalid organization_id for audit log",
        )
        parsed_entity_id = self._parse_uuid(
            entity_id,
            field_name="entity_id",
            error_message="Invalid entity_id for audit log",
        )
        parsed_actor_id = self._parse_uuid(
            actor_id,
            field_name="actor_id",
            error_message="Invalid actor_id for audit log",
        )

        log = AuditLog(
            organization_id=parsed_organization_id,
            actor_type=actor_type,
            actor_id=parsed_actor_id,
            entity_type=entity_type,
            entity_id=parsed_entity_id,
            action=action,
            changes_json=changes_json,
            metadata_json=metadata_json,
        )
        return self.audit_repo.create(log)

    def list_audit_logs(
        self,
        *,
        organization_id: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        action: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> tuple[list[AuditLog], int]:
        parsed_organization_id = self._parse_uuid(
            organization_id,
            field_name="organization_id",
            error_message="Invalid organization_id filter for audit logs",
        )
        parsed_entity_id = self._parse_uuid(
            entity_id,
            field_name="entity_id",
            error_message="Invalid entity_id filter for audit logs",
        )

        return self.audit_repo.list(
            organization_id=parsed_organization_id,
            entity_type=entity_type,
            entity_id=parsed_entity_id,
            action=action,
            page=self._normalize_page(page),
            page_size=self._normalize_page_size(page_size),
        )