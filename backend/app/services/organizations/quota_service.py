from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.models.load_document import LoadDocument
from app.domain.models.staff_user import StaffUser


DEFAULT_QUOTAS: dict[str, int] = {
    "storage_bytes": 5 * 1024 * 1024 * 1024,
    "document_count": 5000,
    "user_count": 25,
    "daily_export_count": 50,
}
WARNING_THRESHOLD = 0.8


@dataclass(frozen=True)
class QuotaDecision:
    allowed: bool
    warning: bool
    reason: str | None
    usage: int
    limit: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "warning": self.warning,
            "reason": self.reason,
            "usage": self.usage,
            "limit": self.limit,
        }


class OrganizationQuotaService:
    """Supportive, warning-first tenant quota foundation.

    Defaults intentionally do not hard-lock tenants. Callers can surface warnings while
    support/admin workflows decide whether to enforce plan-specific limits later.
    """

    def __init__(self, db: Session, quotas: dict[str, int] | None = None) -> None:
        self.db = db
        self.quotas = {**DEFAULT_QUOTAS, **(quotas or {})}

    def storage_usage_bytes(self, organization_id: str) -> int:
        org_uuid = uuid.UUID(str(organization_id))
        return int(
            self.db.scalar(
                select(func.coalesce(func.sum(LoadDocument.file_size_bytes), 0)).where(
                    LoadDocument.organization_id == org_uuid
                )
            )
            or 0
        )

    def document_count(self, organization_id: str) -> int:
        org_uuid = uuid.UUID(str(organization_id))
        return int(
            self.db.scalar(
                select(func.count()).select_from(LoadDocument).where(
                    LoadDocument.organization_id == org_uuid
                )
            )
            or 0
        )

    def user_count(self, organization_id: str) -> int:
        org_uuid = uuid.UUID(str(organization_id))
        return int(
            self.db.scalar(
                select(func.count()).select_from(StaffUser).where(
                    StaffUser.organization_id == org_uuid,
                    StaffUser.removed_at.is_(None),
                )
            )
            or 0
        )

    def can_upload_document(
        self,
        *,
        organization_id: str,
        incoming_size_bytes: int = 0,
        enforce: bool = False,
    ) -> QuotaDecision:
        storage_usage = self.storage_usage_bytes(organization_id) + max(incoming_size_bytes, 0)
        storage_limit = self.quotas["storage_bytes"]
        document_usage = self.document_count(organization_id) + 1
        document_limit = self.quotas["document_count"]
        over_limit = storage_usage > storage_limit or document_usage > document_limit
        warning = over_limit or storage_usage >= int(storage_limit * WARNING_THRESHOLD) or document_usage >= int(document_limit * WARNING_THRESHOLD)
        reason = None
        if over_limit:
            reason = "Organization is over the default document/storage quota. Upload is allowed unless enforcement is enabled."
        elif warning:
            reason = "Organization is approaching the default document/storage quota."
        return QuotaDecision(
            allowed=(not over_limit or not enforce),
            warning=warning,
            reason=reason,
            usage=max(storage_usage, document_usage),
            limit=max(storage_limit, document_limit),
        )

    def can_generate_export(
        self,
        *,
        organization_id: str,
        estimated_rows: int,
        max_rows: int,
        enforce: bool = True,
    ) -> QuotaDecision:
        _ = uuid.UUID(str(organization_id))
        warning = estimated_rows >= int(max_rows * WARNING_THRESHOLD)
        over_limit = estimated_rows > max_rows
        return QuotaDecision(
            allowed=(not over_limit or not enforce),
            warning=warning or over_limit,
            reason="Export row count exceeds the operational safety limit." if over_limit else ("Export is approaching the operational safety limit." if warning else None),
            usage=estimated_rows,
            limit=max_rows,
        )
