from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.domain.models.demo_request import DemoRequest
from app.schemas.common import ApiResponse
from app.schemas.demo_requests import DemoRequestCreateRequest

router = APIRouter()


@router.post("/demo-requests", status_code=status.HTTP_201_CREATED, response_model=ApiResponse)
def create_demo_request(
    payload: DemoRequestCreateRequest,
    db: Session = Depends(get_db_session),
) -> ApiResponse:
    item = DemoRequest(
        full_name=payload.full_name,
        email=str(payload.email).lower(),
        company=payload.company,
        message=payload.message,
        status="received",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return ApiResponse(
        data={"id": str(item.id), "status": item.status, "message": "Demo request received."}
    )
