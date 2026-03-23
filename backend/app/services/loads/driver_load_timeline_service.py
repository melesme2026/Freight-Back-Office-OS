from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.repositories.load_repo import LoadRepository


class DriverLoadTimelineService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.load_repo = LoadRepository(db)

    def get_driver_timeline(
        self,
        *,
        driver_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        loads, total = self.load_repo.list(
            driver_id=driver_id,
            page=page,
            page_size=page_size,
        )

        items = []
        for load in loads:
            items.append(
                {
                    "load_id": str(load.id),
                    "load_number": load.load_number,
                    "status": str(load.status),
                    "processing_status": str(load.processing_status),
                    "pickup_date": load.pickup_date.isoformat() if load.pickup_date else None,
                    "delivery_date": load.delivery_date.isoformat() if load.delivery_date else None,
                    "pickup_location": load.pickup_location,
                    "delivery_location": load.delivery_location,
                    "invoice_number": load.invoice_number,
                    "gross_amount": format(load.gross_amount, "f") if load.gross_amount is not None else None,
                    "currency_code": load.currency_code,
                    "created_at": load.created_at.isoformat(),
                    "updated_at": load.updated_at.isoformat(),
                }
            )

        return {
            "driver_id": driver_id,
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }