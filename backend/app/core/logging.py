from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from app.core.config import get_settings


settings = get_settings()


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)

        if hasattr(record, "request_id"):
            log_record["request_id"] = getattr(record, "request_id")

        if hasattr(record, "organization_id"):
            log_record["organization_id"] = getattr(record, "organization_id")

        if hasattr(record, "customer_account_id"):
            log_record["customer_account_id"] = getattr(record, "customer_account_id")

        if hasattr(record, "load_id"):
            log_record["load_id"] = getattr(record, "load_id")

        return json.dumps(log_record, default=str)


class StandardFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


def _build_stream_handler() -> logging.Handler:
    handler = logging.StreamHandler(sys.stdout)
    if settings.log_json:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(StandardFormatter())
    return handler


def configure_logging() -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level)

    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    root_logger.addHandler(_build_stream_handler())

    logging.getLogger("uvicorn").setLevel(settings.log_level)
    logging.getLogger("uvicorn.error").setLevel(settings.log_level)
    logging.getLogger("uvicorn.access").setLevel(settings.log_level)
    logging.getLogger("sqlalchemy.engine").setLevel(
        "INFO" if settings.sqlalchemy_echo else "WARNING"
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)