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

            if invoice_number and load.invoice_number == invoice_number:
                score += 100
                reasons.append("invoice_number")

            if load_number and load.load_number == load_number:
                score += 80
                reasons.append("load_number")

            if rate_confirmation_number and load.rate_confirmation_number == rate_confirmation_number:
                score += 70
                reasons.append("rate_confirmation_number")

            if bol_number and load.bol_number == bol_number:
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