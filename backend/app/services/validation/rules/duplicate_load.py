from __future__ import annotations

from typing import Any


class DuplicateLoadRule:
    rule_code = "duplicate_load"

    def evaluate(self, *, payload: dict[str, Any]) -> list[dict[str, Any]]:
        duplicate_candidates = payload.get("duplicate_candidates", [])

        if not duplicate_candidates:
            return []

        return [
            {
                "rule_code": self.rule_code,
                "severity": "warning",
                "title": "Possible duplicate load",
                "description": (
                    "Potential duplicate load detected based on matching load identifiers "
                    f"or document metadata. Candidates found: {len(duplicate_candidates)}."
                ),
                "is_blocking": False,
            }
        ]