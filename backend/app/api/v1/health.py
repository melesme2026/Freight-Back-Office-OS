from __future__ import annotations

from fastapi import APIRouter

from app.core.healthchecks import get_basic_health_status, get_readiness_status


router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {
        "data": get_basic_health_status(),
        "meta": {},
        "error": None,
    }


@router.get("/health/readiness")
def readiness() -> dict:
    return {
        "data": get_readiness_status(),
        "meta": {},
        "error": None,
    }