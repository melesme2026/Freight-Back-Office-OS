from __future__ import annotations

from typing import Any

from app.core.exceptions import ValidationError
from app.domain.enums.channel import Channel
from app.services.ingestion.ingestion_router import IngestionRouter


class ChannelDispatcher:
    def __init__(self, ingestion_router: IngestionRouter) -> None:
        self.ingestion_router = ingestion_router

    def dispatch(
        self,
        *,
        channel: Channel,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return self.ingestion_router.route(channel=channel, payload=payload)

    def dispatch_from_value(
        self,
        *,
        channel_value: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            channel = Channel(channel_value)
        except ValueError as exc:
            raise ValidationError(
                "Invalid channel",
                details={"channel": channel_value},
            ) from exc

        return self.dispatch(channel=channel, payload=payload)