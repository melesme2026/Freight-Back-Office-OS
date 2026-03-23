from __future__ import annotations

from typing import Any


class TicketRoutingService:
    def route(
        self,
        *,
        priority: str,
        customer_account_id: str | None = None,
        load_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized_priority = (priority or "normal").strip().lower()
        metadata = metadata or {}

        queue = "general_support"

        if normalized_priority in {"urgent", "high"}:
            queue = "priority_support"
        elif load_id:
            queue = "operations_support"
        elif customer_account_id:
            queue = "account_support"

        return {
            "queue": queue,
            "priority": normalized_priority,
            "metadata": metadata,
        }