from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.domain.models.validation_issue import ValidationIssue
from app.repositories.validation_repo import ValidationRepository
from app.services.validation.rules.amount_mismatch import AmountMismatchRule
from app.services.validation.rules.broker_consistency import BrokerConsistencyRule
from app.services.validation.rules.duplicate_load import DuplicateLoadRule
from app.services.validation.rules.missing_required_fields import (
    MissingRequiredFieldsRule,
)
from app.services.validation.rules.missing_signature import MissingSignatureRule
from app.services.validation.rules.unreadable_document import UnreadableDocumentRule
from app.services.validation.validation_engine import ValidationEngine
from app.services.validation.validation_issue_generator import ValidationIssueGenerator
from sqlalchemy import select
from sqlalchemy.orm import Session


class ValidationOrchestrator:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.validation_repo = ValidationRepository(db)
        self.engine = ValidationEngine(
            rules=[
                MissingRequiredFieldsRule(),
                MissingSignatureRule(),
                AmountMismatchRule(),
                DuplicateLoadRule(),
                UnreadableDocumentRule(),
                BrokerConsistencyRule(),
            ]
        )

    def validate_load(
        self,
        *,
        organization_id: str,
        load_id: str,
        document_id: str | None = None,
        payload: dict[str, Any],
    ) -> list[ValidationIssue]:
        canonical_issues = ValidationIssueGenerator(self.db).generate(
            organization_id=organization_id,
            load_id=load_id,
            document_id=document_id,
            payload=payload,
        )
        results = self.engine.run(payload=payload)

        issues: list[ValidationIssue] = []
        now = datetime.now(timezone.utc)

        canonical_rule_codes = {issue.rule_code for issue in canonical_issues}
        result_rule_codes = [str(item["rule_code"]) for item in results]
        if result_rule_codes:
            canonical_rule_codes.update(
                self.db.scalars(
                    select(ValidationIssue.rule_code).where(
                        ValidationIssue.organization_id == organization_id,
                        ValidationIssue.load_id == load_id,
                        ValidationIssue.document_id == document_id,
                        ValidationIssue.is_resolved.is_(False),
                        ValidationIssue.rule_code.in_(result_rule_codes),
                    )
                ).all()
            )

        for item in results:
            if item["rule_code"] in canonical_rule_codes:
                continue
            issue = ValidationIssue(
                organization_id=organization_id,
                load_id=load_id,
                document_id=document_id,
                rule_code=item["rule_code"],
                severity=item["severity"],
                title=item["title"],
                description=item["description"],
                is_blocking=item.get("is_blocking", False),
                is_resolved=False,
                resolved_by_staff_user_id=None,
                resolved_at=None,
                resolution_notes=None,
                created_at=now,
                updated_at=now,
            )
            issues.append(issue)

        if issues:
            canonical_issues.extend(self.validation_repo.create_many(issues))

        return canonical_issues
