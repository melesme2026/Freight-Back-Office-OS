from __future__ import annotations

import os
import uuid
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL_OVERRIDE", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("CELERY_BROKER_URL", "memory://")
os.environ.setdefault("CELERY_RESULT_BACKEND", "cache+memory://")

from app.core.database import Base, init_db  # noqa: E402


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type, _compiler, **_kwargs) -> str:
    return "JSON"


@compiles(PGUUID, "sqlite")
def _compile_uuid_sqlite(_type, _compiler, **_kwargs) -> str:
    return "CHAR(32)"


_ORIGINAL_UUID_BIND_PROCESSOR = PGUUID.bind_processor
_ORIGINAL_UUID_RESULT_PROCESSOR = PGUUID.result_processor


def _patched_uuid_bind_processor(self, dialect):
    processor = _ORIGINAL_UUID_BIND_PROCESSOR(self, dialect)
    if dialect.name != "sqlite":
        return processor

    def process(value):
        if isinstance(value, str):
            try:
                value = uuid.UUID(value)
            except ValueError:
                return value
        if processor is None:
            return value
        return processor(value)

    return process


PGUUID.bind_processor = _patched_uuid_bind_processor


def _patched_uuid_result_processor(self, dialect, coltype):
    processor = _ORIGINAL_UUID_RESULT_PROCESSOR(self, dialect, coltype)
    if dialect.name != "sqlite":
        return processor

    def process(value):
        if isinstance(value, int):
            value = f"{value:032x}"
        if processor is None:
            return value
        return processor(value)

    return process


PGUUID.result_processor = _patched_uuid_result_processor


@pytest.fixture(scope="session")
def engine():
    init_db(import_models=True)

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def db_session(engine) -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()

    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=connection,
        future=True,
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
