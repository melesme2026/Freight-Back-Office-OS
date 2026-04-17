from __future__ import annotations

from app.domain.enums.compat import StrEnum


class Channel(StrEnum):
    WEB = "web"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    API = "api"
    MANUAL = "manual"
    DRIVER_PORTAL = "driver_portal"
