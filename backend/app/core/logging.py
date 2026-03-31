from __future__ import annotations

import logging
import sys
import traceback
from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# -----------------------------------------
# LOGGER SETUP
# -----------------------------------------
LOGGER_NAME = "freight-backoffice"
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

logger = logging.getLogger(LOGGER_NAME)


def configure_logging(level: int | str = logging.INFO) -> None:
    """
    Idempotent logging configuration for local/dev/container startup.
    Prevents duplicate handlers under reload and guarantees the symbol
    expected by app.main exists.
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
    logger.setLevel(resolved_level)

    logging.getLogger("uvicorn").setLevel(resolved_level)
    logging.getLogger("uvicorn.error").setLevel(resolved_level)
    logging.getLogger("uvicorn.access").setLevel(resolved_level)


# -----------------------------------------
# BASE ERROR CLASSES
# -----------------------------------------
class AppError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str = "app_error",
        details: Mapping[str, Any] | None = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = dict(details or {})
        self.status_code = status_code


class ValidationError(AppError):
    def __init__(self, message: str = "Validation failed", *, details: Mapping[str, Any] | None = None):
        super().__init__(
            message,
            code="validation_error",
            details=details,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Unauthorized", *, details: Mapping[str, Any] | None = None):
        super().__init__(
            message,
            code="unauthorized",
            details=details,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class ForbiddenError(AppError):
    def __init__(self, message: str = "Forbidden", *, details: Mapping[str, Any] | None = None):
        super().__init__(
            message,
            code="forbidden",
            details=details,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found", *, details: Mapping[str, Any] | None = None):
        super().__init__(
            message,
            code="not_found",
            details=details,
            status_code=status.HTTP_404_NOT_FOUND,
        )


class ConflictError(AppError):
    def __init__(self, message: str = "Conflict", *, details: Mapping[str, Any] | None = None):
        super().__init__(
            message,
            code="conflict",
            details=details,
            status_code=status.HTTP_409_CONFLICT,
        )


class ExternalServiceError(AppError):
    def __init__(self, message: str = "External service error", *, details: Mapping[str, Any] | None = None):
        super().__init__(
            message,
            code="external_service_error",
            details=details,
            status_code=status.HTTP_502_BAD_GATEWAY,
        )


class RateLimitError(AppError):
    def __init__(self, message: str = "Rate limit exceeded", *, details: Mapping[str, Any] | None = None):
        super().__init__(
            message,
            code="rate_limit_exceeded",
            details=details,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )


# -----------------------------------------
# RESPONSE BUILDER
# -----------------------------------------
def _build_error_response(
    *,
    request: Request,
    message: str,
    code: str,
    status_code: int,
    details: Mapping[str, Any] | None = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)

    return JSONResponse(
        status_code=status_code,
        content={
            "data": None,
            "meta": {
                "request_id": request_id,
            },
            "error": {
                "code": code,
                "message": message,
                "details": dict(details or {}),
            },
        },
    )


# -----------------------------------------
# LOGGING HELPERS
# -----------------------------------------
def _log_error(
    *,
    request: Request,
    level: str,
    message: str,
    code: str,
    details: Mapping[str, Any] | None = None,
    exc: Exception | None = None,
) -> None:
    log_payload = {
        "request_id": getattr(request.state, "request_id", None),
        "path": request.url.path,
        "method": request.method,
        "code": code,
        "message": message,
        "details": dict(details or {}),
    }

    if exc is not None:
        log_payload["exception"] = str(exc)
        log_payload["trace"] = traceback.format_exc()

    getattr(logger, level)(log_payload)


# -----------------------------------------
# HANDLERS
# -----------------------------------------
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    _log_error(
        request=request,
        level="warning",
        message=exc.message,
        code=exc.code,
        details=exc.details,
    )

    return _build_error_response(
        request=request,
        message=exc.message,
        code=exc.code,
        status_code=exc.status_code,
        details=exc.details,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    _log_error(
        request=request,
        level="warning",
        message=str(exc.detail),
        code="http_error",
    )

    return _build_error_response(
        request=request,
        message=str(exc.detail) if exc.detail else "HTTP error",
        code="http_error",
        status_code=exc.status_code,
    )


async def request_validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    _log_error(
        request=request,
        level="warning",
        message="Request validation failed",
        code="request_validation_error",
        details={"errors": exc.errors()},
    )

    return _build_error_response(
        request=request,
        message="Request validation failed",
        code="request_validation_error",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        details={"errors": exc.errors()},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    _log_error(
        request=request,
        level="error",
        message="Unhandled exception",
        code="internal_server_error",
        exc=exc,
    )

    return _build_error_response(
        request=request,
        message="Internal server error",
        code="internal_server_error",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


# -----------------------------------------
# REGISTER
# -----------------------------------------
def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)