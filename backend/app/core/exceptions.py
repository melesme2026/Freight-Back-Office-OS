from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


logger = logging.getLogger(__name__)


class AppError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str = "app_error",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = dict(details or {})


class ValidationError(AppError):
    def __init__(
        self,
        message: str = "Validation failed",
        *,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code="validation_error",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class NotFoundError(AppError):
    def __init__(
        self,
        message: str = "Resource not found",
        *,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code="not_found",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class UnauthorizedError(AppError):
    def __init__(
        self,
        message: str = "Unauthorized",
        *,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code="unauthorized",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class ForbiddenError(AppError):
    def __init__(
        self,
        message: str = "Forbidden",
        *,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code="forbidden",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class ConflictError(AppError):
    def __init__(
        self,
        message: str = "Conflict",
        *,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code="conflict",
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class InvalidTransitionError(AppError):
    def __init__(
        self,
        message: str = "Invalid workflow transition",
        *,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code="invalid_transition",
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class DuplicateRecordError(AppError):
    def __init__(
        self,
        message: str = "Duplicate record",
        *,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code="duplicate_record",
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class ProcessingError(AppError):
    def __init__(
        self,
        message: str = "Processing failed",
        *,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code="processing_failed",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class BillingError(AppError):
    def __init__(
        self,
        message: str = "Billing error",
        *,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code="billing_error",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class PaymentError(AppError):
    def __init__(
        self,
        message: str = "Payment failed",
        *,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code="payment_failed",
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            details=details,
        )


class WebhookSignatureError(AppError):
    def __init__(
        self,
        message: str = "Webhook signature invalid",
        *,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code="webhook_signature_invalid",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class UnsupportedFileTypeError(AppError):
    def __init__(
        self,
        message: str = "Unsupported file type",
        *,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code="unsupported_file_type",
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            details=details,
        )


def _build_error_payload(
    *,
    request: Request | None,
    code: str,
    message: str,
    details: Mapping[str, Any] | None = None,
    meta: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload_meta = dict(meta or {})

    if request is not None:
        request_id = getattr(request.state, "request_id", None)
        if request_id:
            payload_meta["request_id"] = request_id

    return {
        "data": None,
        "meta": payload_meta,
        "error": {
            "code": code,
            "message": message,
            "details": dict(details or {}),
        },
    }


def _log_exception(
    *,
    request: Request,
    message: str,
    code: str,
    status_code: int,
    details: Mapping[str, Any] | None = None,
    exc_info: bool = False,
) -> None:
    logger.error(
        "API exception",
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "path": str(request.url.path),
            "method": request.method,
            "error_code": code,
            "status_code": status_code,
            "error_message": message,
            "error_details": dict(details or {}),
        },
        exc_info=exc_info,
    )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    _log_exception(
        request=request,
        message=exc.message,
        code=exc.code,
        status_code=exc.status_code,
        details=exc.details,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=_build_error_payload(
            request=request,
            code=exc.code,
            message=exc.message,
            details=exc.details,
        ),
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    details: dict[str, Any] = {}
    if exc.detail is not None and not isinstance(exc.detail, str):
        details["detail"] = exc.detail

    message = str(exc.detail) if exc.detail is not None else "HTTP error"

    _log_exception(
        request=request,
        message=message,
        code="http_error",
        status_code=exc.status_code,
        details=details,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=_build_error_payload(
            request=request,
            code="http_error",
            message=message,
            details=details,
        ),
    )


async def request_validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    details = {"errors": exc.errors()}
    _log_exception(
        request=request,
        message="Request validation failed",
        code="request_validation_error",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        details=details,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_build_error_payload(
            request=request,
            code="request_validation_error",
            message="Request validation failed",
            details=details,
        ),
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    details = {"exception_type": exc.__class__.__name__}
    _log_exception(
        request=request,
        message="An unexpected error occurred",
        code="internal_server_error",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        details=details,
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_build_error_payload(
            request=request,
            code="internal_server_error",
            message="An unexpected error occurred",
            details=details,
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(
        RequestValidationError,
        request_validation_error_handler,
    )
    app.add_exception_handler(Exception, unhandled_exception_handler)