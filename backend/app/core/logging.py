from __future__ import annotations

import logging
import sys


LOGGER_NAME = "freight-backoffice"
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

logger = logging.getLogger(LOGGER_NAME)


def configure_logging(level: int | str = logging.INFO) -> None:
    """
    Idempotent logging configuration for local/dev/container startup.

    - Prevents duplicate handlers under reload
    - Ensures stdout logging for container-friendly operation
    - Keeps root + app + uvicorn loggers aligned
    """
    root_logger = logging.getLogger()

    if isinstance(level, str):
        resolved_level = logging.getLevelName(level.upper())
        if not isinstance(resolved_level, int):
            resolved_level = logging.INFO
    else:
        resolved_level = level

    formatter = logging.Formatter(LOG_FORMAT)

    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
    else:
        for handler in root_logger.handlers:
            handler.setFormatter(formatter)

    root_logger.setLevel(resolved_level)

    app_logger = logging.getLogger(LOGGER_NAME)
    app_logger.setLevel(resolved_level)
    app_logger.propagate = True

    logging.getLogger("uvicorn").setLevel(resolved_level)
    logging.getLogger("uvicorn.error").setLevel(resolved_level)
    logging.getLogger("uvicorn.access").setLevel(resolved_level)