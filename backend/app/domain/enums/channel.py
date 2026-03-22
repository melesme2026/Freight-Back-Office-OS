from __future__ import annotations

from enum import StrEnum


class Channel(StrEnum):
    WEB = "web"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    API = "api"
    MANUAL = "manual"