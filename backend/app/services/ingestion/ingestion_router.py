from __future__ import annotations

from typing import Any

from app.domain.enums.channel import Channel
from app.services.ingestion.api_ingestion_service import ApiIngestionService
from app.services.ingestion.email_ingestion_service import EmailIngestionService
from app.services.ingestion.upload_service import UploadService
from app.services.ingestion.whatsapp_ingestion_service import WhatsAppIngestionService


class IngestionRouter:
    def __init__(
        self,
        *,
        upload_service: UploadService,
        whatsapp_ingestion_service: WhatsAppIngestionService,
        email_ingestion_service: EmailIngestionService,
        api_ingestion_service: ApiIngestionService,
    ) -> None:
        self.upload_service = upload_service
        self.whatsapp_ingestion_service = whatsapp_ingestion_service
        self.email_ingestion_service = email_ingestion_service
        self.api_ingestion_service = api_ingestion_service

    def route(
        self,
        *,
        channel: Channel,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if channel == Channel.WHATSAPP:
            return self.whatsapp_ingestion_service.ingest(payload)

        if channel == Channel.EMAIL:
            return self.email_ingestion_service.ingest(payload)

        if channel == Channel.API:
            return self.api_ingestion_service.ingest(payload)

        return self.upload_service.ingest(payload)