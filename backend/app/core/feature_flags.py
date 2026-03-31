from __future__ import annotations

from dataclasses import asdict, dataclass

from app.core.config import Settings, get_settings


@dataclass(frozen=True, slots=True)
class FeatureFlags:
    ai_enabled: bool
    whatsapp_enabled: bool
    email_enabled: bool
    billing_enabled: bool

    def as_dict(self) -> dict[str, bool]:
        return asdict(self)

    def is_enabled(self, feature_name: str) -> bool:
        try:
            value = getattr(self, feature_name)
        except AttributeError as exc:
            raise KeyError(f"Unknown feature flag: {feature_name}") from exc

        if not isinstance(value, bool):
            raise KeyError(f"Unknown feature flag: {feature_name}")

        return value


def get_feature_flags(settings: Settings | None = None) -> FeatureFlags:
    app_settings = settings or get_settings()

    return FeatureFlags(
        ai_enabled=app_settings.ai_enabled,
        whatsapp_enabled=app_settings.whatsapp_enabled,
        email_enabled=app_settings.email_enabled,
        billing_enabled=app_settings.billing_enabled,
    )