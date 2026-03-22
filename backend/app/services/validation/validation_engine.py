from __future__ import annotations

from typing import Any, Protocol


class ValidationRule(Protocol):
    rule_code: str

    def evaluate(self, *, payload: dict[str, Any]) -> list[dict[str, Any]]:
        ...


class ValidationEngine:
    def __init__(self, rules: list[ValidationRule] | None = None) -> None:
        self.rules = rules or []

    def register_rule(self, rule: ValidationRule) -> None:
        self.rules.append(rule)

    def run(self, *, payload: dict[str, Any]) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []

        for rule in self.rules:
            results = rule.evaluate(payload=payload)
            if results:
                issues.extend(results)

        return issues