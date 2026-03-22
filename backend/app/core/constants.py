from __future__ import annotations

from app.core.config import get_settings


settings = get_settings()

APP_NAME = settings.app_name
APP_VERSION = settings.app_version
API_V1_PREFIX = settings.api_v1_prefix

DEFAULT_TIMEZONE = "America/Toronto"
DEFAULT_CURRENCY_CODE = "USD"

REQUEST_ID_HEADER = "X-Request-ID"

SUPPORTED_UPLOAD_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}

MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024

LOAD_STATUS_NEW = "new"
LOAD_STATUS_DOCS_RECEIVED = "docs_received"
LOAD_STATUS_EXTRACTING = "extracting"
LOAD_STATUS_NEEDS_REVIEW = "needs_review"
LOAD_STATUS_VALIDATED = "validated"
LOAD_STATUS_READY_TO_SUBMIT = "ready_to_submit"
LOAD_STATUS_SUBMITTED = "submitted"
LOAD_STATUS_FUNDED = "funded"
LOAD_STATUS_PAID = "paid"
LOAD_STATUS_EXCEPTION = "exception"
LOAD_STATUS_ARCHIVED = "archived"

PROCESSING_STATUS_PENDING = "pending"
PROCESSING_STATUS_IN_PROGRESS = "in_progress"
PROCESSING_STATUS_COMPLETED = "completed"
PROCESSING_STATUS_FAILED = "failed"

CHANNEL_WEB = "web"
CHANNEL_WHATSAPP = "whatsapp"
CHANNEL_EMAIL = "email"
CHANNEL_API = "api"
CHANNEL_MANUAL = "manual"

DOCUMENT_TYPE_RATE_CONFIRMATION = "rate_confirmation"
DOCUMENT_TYPE_BILL_OF_LADING = "bill_of_lading"
DOCUMENT_TYPE_INVOICE = "invoice"
DOCUMENT_TYPE_PROOF_OF_DELIVERY = "proof_of_delivery"
DOCUMENT_TYPE_OTHER = "other"
DOCUMENT_TYPE_UNKNOWN = "unknown"

NOTIFICATION_CHANNEL_WHATSAPP = "whatsapp"
NOTIFICATION_CHANNEL_EMAIL = "email"
NOTIFICATION_CHANNEL_SMS = "sms"
NOTIFICATION_CHANNEL_IN_APP = "in_app"

NOTIFICATION_STATUS_QUEUED = "queued"
NOTIFICATION_STATUS_SENT = "sent"
NOTIFICATION_STATUS_DELIVERED = "delivered"
NOTIFICATION_STATUS_READ = "read"
NOTIFICATION_STATUS_FAILED = "failed"
NOTIFICATION_STATUS_RECEIVED = "received"

ROLE_OWNER = "owner"
ROLE_ADMIN = "admin"
ROLE_OPS_MANAGER = "ops_manager"
ROLE_OPS_AGENT = "ops_agent"
ROLE_BILLING_ADMIN = "billing_admin"
ROLE_SUPPORT_AGENT = "support_agent"
ROLE_VIEWER = "viewer"