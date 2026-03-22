from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class FeatureFlags:
    ai_enabled: bool
    whatsapp_enabled: bool
    email_enabled: bool
    billing_enabled: bool


def get_feature_flags(settings: Settings | None = None) -> FeatureFlags:
    app_settings = settings or get_settings()
    return FeatureFlags(
        ai_enabled=app_settings.ai_enabled,
        whatsapp_enabled=app_settings.whatsapp_enabled,
        email_enabled=app_settings.email_enabled,
        billing_enabled=app_settings.billing_enabled,
    )