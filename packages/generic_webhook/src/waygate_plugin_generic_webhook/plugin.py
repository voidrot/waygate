from uuid_utils import uuid4
from waygate_plugin_generic_webhook.models import GenericWebhookPayload
from collections.abc import Mapping

from pydantic import BaseModel
from datetime import datetime, timezone
from waygate_core.schema import RawDocument
from waygate_core.plugin import WebhookPlugin, hookimpl
from . import PLUGIN_NAME, __version__


class GenericWebhookProvider(WebhookPlugin):
    @staticmethod
    @hookimpl
    def waygate_webhook_plugin() -> type[WebhookPlugin]:
        return GenericWebhookProvider

    @property
    def name(self) -> str:
        return PLUGIN_NAME

    @property
    def description(self) -> str:
        return "A generic webhook plugin for WayGate that can be configured to handle various webhook payloads."

    @property
    def version(self) -> str:
        return __version__

    @property
    def openapi_payload_schema(self) -> type[BaseModel]:
        return GenericWebhookPayload

    async def enrich_webhook_payload(
        self, payload: dict, headers: Mapping[str, str]
    ) -> dict:
        # For demonstration purposes, we'll just return the original payload without enrichment.
        # In a real implementation, you could add logic here to fetch additional data based on the payload and headers, and include it in the enriched payload.
        return payload

    async def handle_webhook(self, payload: dict) -> list[RawDocument]:
        return await self._build_documents_from_payload(
            GenericWebhookPayload.model_validate(payload)
        )

    async def verify_webhook_request(
        self, headers: Mapping[str, str], body: bytes
    ) -> None:
        # For demonstration purposes, we'll just accept all requests.
        # In a real implementation, you would add logic here to verify the request (e.g. check signatures).
        return None

    async def _build_documents_from_payload(
        self, payload: GenericWebhookPayload
    ) -> list[RawDocument]:
        documents = []
        for doc in payload.documents:
            doc_topics = (
                payload.metadata.topics + doc.metadata.get("topics", [])
                if doc.metadata
                else payload.metadata.topics
            )
            doc_tags = (
                payload.metadata.tags + doc.metadata.get("tags", [])
                if doc.metadata
                else payload.metadata.tags
            )
            raw_doc = RawDocument(
                source_type=PLUGIN_NAME,
                source_id=doc.document_name or None,
                source_hash=doc.document_hash or None,
                source_uri=doc.document_path or None,
                timestamp=datetime.strptime(
                    payload.metadata.originated_at, "%Y-%m-%dT%H:%M:%S.%fZ"
                )
                if payload.metadata.originated_at
                else datetime.now(timezone.utc),
                doc_id=str(uuid4()),
                content=doc.content,
                topics=doc_topics,
                tags=doc_tags,
            )
            documents.append(raw_doc)
        return documents
