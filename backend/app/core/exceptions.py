from __future__ import annotations

from typing import Any


class AppError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str = "app_error",
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class ValidationError(AppError):
    def __init__(
        self,
        message: str = "Validation failed",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code="validation_error",
            status_code=422,
            details=details,
        )


class NotFoundError(AppError):
    def __init__(
        self,
        message: str = "Resource not found",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code="not_found",
            status_code=404,
            details=details,
        )


class UnauthorizedError(AppError):
    def __init__(
        self,
        message: str = "Unauthorized",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code="unauthorized",
            status_code=401,
            details=details,
        )


class ForbiddenError(AppError):
    def __init__(
        self,
        message: str = "Forbidden",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code="forbidden",
            status_code=403,
            details=details,
        )


class ConflictError(AppError):
    def __init__(
        self,
        message: str = "Conflict",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code="conflict",
            status_code=409,
            details=details,
        )


class InvalidTransitionError(AppError):
    def __init__(
        self,
        message: str = "Invalid workflow transition",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code="invalid_transition",
            status_code=409,
            details=details,
        )


class DuplicateRecordError(AppError):
    def __init__(
        self,
        message: str = "Duplicate record",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code="duplicate_record",
            status_code=409,
            details=details,
        )


class ProcessingError(AppError):
    def __init__(
        self,
        message: str = "Processing failed",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code="processing_failed",
            status_code=500,
            details=details,
        )


class BillingError(AppError):
    def __init__(
        self,
        message: str = "Billing error",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code="billing_error",
            status_code=400,
            details=details,
        )


class PaymentError(AppError):
    def __init__(
        self,
        message: str = "Payment failed",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code="payment_failed",
            status_code=402,
            details=details,
        )


class WebhookSignatureError(AppError):
    def __init__(
        self,
        message: str = "Webhook signature invalid",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code="webhook_signature_invalid",
            status_code=401,
            details=details,
        )


class UnsupportedFileTypeError(AppError):
    def __init__(
        self,
        message: str = "Unsupported file type",
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code="unsupported_file_type",
            status_code=415,
            details=details,
        )