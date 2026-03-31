from __future__ import annotations

from collections import defaultdict
from typing import Any


class TemplateService:
    def render(
        self,
        *,
        template_name: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        normalized_template_name = str(template_name).strip().lower()
        context = context or {}

        templates = {
            "load_received": (
                "Your load documents were received successfully. "
                "Load: {load_number}"
            ),
            "invoice_submitted": (
                "Your invoice has been submitted. "
                "Invoice: {invoice_number}"
            ),
            "payment_received": (
                "Payment received successfully. "
                "Amount: {amount}"
            ),
            "generic_status_update": (
                "Status update: {status}"
            ),
        }

        template = templates.get(normalized_template_name, "{message}")
        safe_context = defaultdict(
            str,
            {
                "load_number": context.get("load_number", "N/A"),
                "invoice_number": context.get("invoice_number", "N/A"),
                "amount": context.get("amount", "N/A"),
                "status": context.get("status", "N/A"),
                "message": context.get("message", ""),
            },
        )

        return template.format_map(safe_context)