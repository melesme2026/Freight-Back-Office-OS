from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db


def get_app_settings() -> Settings:
    return get_settings()


def get_db_session(db: Session = Depends(get_db)) -> Generator[Session, None, None]:
    try:
        yield db
    finally:
        pass