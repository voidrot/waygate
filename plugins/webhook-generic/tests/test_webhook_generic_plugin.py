import asyncio
from datetime import datetime, timezone

import pytest

from waygate_plugin_webhook_generic.models import GenericWebhookPayload
from waygate_plugin_webhook_generic.plugin import (
    GenericWebhookConfig,
    GenericWebhookPlugin,
    _parse_originated_at,
)


def test_plugin_registers_webhook_hook() -> None:
    assert GenericWebhookPlugin.waygate_webhook_plugin() is GenericWebhookPlugin


def test_plugin_registers_config_hook() -> None:
    registration = GenericWebhookPlugin.waygate_plugin_config()

    assert registration.name == "generic-webhook"
    assert registration.config is GenericWebhookConfig


def test_openapi_payload_schema_declares_generic_payload() -> None:
    plugin = GenericWebhookPlugin()

    assert plugin.openapi_payload_schema is GenericWebhookPayload


def test_verify_and_enrich_defaults_are_passthrough() -> None:
    plugin = GenericWebhookPlugin()
    headers = {"x-test": "1"}
    body = b'{"ok":true}'
    payload = {"ok": True}

    asyncio.run(plugin.verify_webhook_request(headers, body))
    enriched = asyncio.run(plugin.enrich_webhook_payload(payload, headers))

    assert enriched is payload


def test_handle_webhook_maps_documents_with_stable_deduped_topics_and_tags() -> None:
    plugin = GenericWebhookPlugin()
    payload = {
        "metadata": {
            "event": "document.created",
            "source": "tests",
            "topics": ["alpha", "shared", "  ", "alpha"],
            "tags": ["tag-1", "dup", "dup"],
            "originated_at": "2026-04-18T10:30:45.123456Z",
        },
        "documents": [
            {
                "document_type": "markdown",
                "document_name": "doc-one.md",
                "document_path": "docs/doc-one.md",
                "document_hash": "sha256:abc123",
                "content": "# one",
                "metadata": {
                    "topics": ["shared", "beta", "beta", "gamma"],
                    "tags": ["dup", "tag-2", ""],
                },
            }
        ],
    }

    documents = asyncio.run(plugin.handle_webhook(payload))

    assert len(documents) == 1
    document = documents[0]
    assert document.source_type == "generic-webhook"
    assert document.content_type == "text/markdown"
    assert document.source_id == "doc-one.md"
    assert document.source_uri == "docs/doc-one.md"
    assert document.source_hash == "sha256:abc123"
    assert document.content == "# one"
    assert document.topics == ["alpha", "shared", "beta", "gamma"]
    assert document.tags == ["tag-1", "dup", "tag-2"]
    assert document.timestamp == datetime(
        2026, 4, 18, 10, 30, 45, 123456, tzinfo=timezone.utc
    )


def test_handle_webhook_uses_current_utc_time_when_originated_at_missing() -> None:
    plugin = GenericWebhookPlugin()
    payload = {
        "metadata": {
            "event": "document.created",
            "source": "tests",
        },
        "documents": [
            {
                "document_type": "markdown",
                "content": "# one",
            }
        ],
    }

    before = datetime.now(timezone.utc)
    documents = asyncio.run(plugin.handle_webhook(payload))
    after = datetime.now(timezone.utc)

    assert len(documents) == 1
    timestamp = documents[0].timestamp
    assert timestamp.tzinfo is not None
    assert before <= timestamp <= after


def test_handle_webhook_rejects_invalid_document_metadata_list_shape() -> None:
    plugin = GenericWebhookPlugin()
    payload = {
        "metadata": {
            "event": "document.created",
            "source": "tests",
        },
        "documents": [
            {
                "document_type": "markdown",
                "content": "# one",
                "metadata": {"tags": "not-a-list"},
            }
        ],
    }

    with pytest.raises(
        ValueError,
        match="Document metadata 'tags' must be a list of strings",
    ):
        asyncio.run(plugin.handle_webhook(payload))


def test_handle_webhook_rejects_payload_validation_errors() -> None:
    plugin = GenericWebhookPlugin()

    with pytest.raises(ValueError, match="Invalid generic webhook payload"):
        asyncio.run(plugin.handle_webhook({"documents": []}))


def test_parse_originated_at_requires_timezone() -> None:
    with pytest.raises(
        ValueError,
        match="Invalid originated_at timestamp, timezone is required",
    ):
        _parse_originated_at("2026-04-18T10:30:45")
