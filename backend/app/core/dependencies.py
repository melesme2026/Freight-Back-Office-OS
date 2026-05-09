from __future__ import annotations

from typing import Annotated

from app.core.config import Settings, get_settings
from app.core.database import get_db
from fastapi import Depends
from sqlalchemy.orm import Session


def get_app_settings() -> Settings:
    return get_settings()


def get_db_session(
    db: Annotated[Session, Depends(get_db)],
) -> Session:
    return db
