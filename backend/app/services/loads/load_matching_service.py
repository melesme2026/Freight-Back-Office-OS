from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.repositories.load_repo import LoadRepository


class LoadMatchingService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.load_repo = LoadRepository(db)

    def find_candidate_loads(
        self,
        *,
        organization_id: str,
        invoice_number: str | None = None,
        load_number: str | None = None,
        rate_confirmation_number: str | None = None,
        bol_number: str | None = None,
    ) -> list[dict[str, Any]]:
        normalized_invoice_number = self._normalize_match_value(invoice_number)
        normalized_load_number = self._normalize_match_value(load_number)
        normalized_rate_confirmation_number = self._normalize_match_value(rate_confirmation_number)
        normalized_bol_number = self._normalize_match_value(bol_number)

        if not any(
            [
                normalized_invoice_number,
                normalized_load_number,
                normalized_rate_confirmation_number,
                normalized_bol_number,
            ]
        ):
            return []

        candidates: list[dict[str, Any]] = []

        page = 1
        page_size = 100

        loads, _ = self.load_repo.list(
            organization_id=organization_id,
            page=page,
            page_size=page_size,
        )

        for load in loads:
            score = 0
            reasons: list[str] = []

            load_invoice_number = self._normalize_match_value(load.invoice_number)
            load_load_number = self._normalize_match_value(load.load_number)
            load_rate_confirmation_number = self._normalize_match_value(
                load.rate_confirmation_number
            )
            load_bol_number = self._normalize_match_value(load.bol_number)

            if normalized_invoice_number and load_invoice_number == normalized_invoice_number:
                score += 100
                reasons.append("invoice_number")

            if normalized_load_number and load_load_number == normalized_load_number:
                score += 80
                reasons.append("load_number")

            if (
                normalized_rate_confirmation_number
                and load_rate_confirmation_number == normalized_rate_confirmation_number
            ):
                score += 70
                reasons.append("rate_confirmation_number")

            if normalized_bol_number and load_bol_number == normalized_bol_number:
                score += 60
                reasons.append("bol_number")

            if score > 0:
                candidates.append(
                    {
                        "load_id": str(load.id),
                        "score": score,
                        "reasons": reasons,
                    }
                )

        candidates.sort(key=lambda item: item["score"], reverse=True)
        return candidates

    def best_match(
        self,
        *,
        organization_id: str,
        invoice_number: str | None = None,
        load_number: str | None = None,
        rate_confirmation_number: str | None = None,
        bol_number: str | None = None,
    ) -> dict[str, Any] | None:
        candidates = self.find_candidate_loads(
            organization_id=organization_id,
            invoice_number=invoice_number,
            load_number=load_number,
            rate_confirmation_number=rate_confirmation_number,
            bol_number=bol_number,
        )

        if not candidates:
            return None

        return candidates[0]

    @staticmethod
    def _normalize_match_value(value: Any) -> str | None:
        if value is None:
            return None

        normalized = str(value).strip().lower()
        return normalized or None