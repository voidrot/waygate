from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time

import pytest
from pydantic import ValidationError

from waygate_core.plugin import WorkflowTriggerMessage
from waygate_core.plugin.webhook import WebhookVerificationError
from waygate_core.schema.visibility import Visibility
from waygate_plugin_webhook_agent_session.models import AgentSessionWebhookPayload
from waygate_plugin_webhook_agent_session.plugin import (
    AgentSessionWebhookConfig,
    AgentSessionWebhookPlugin,
)


def _payload() -> dict:
    return {
        "schema_version": "v1",
        "capture_adapter": "vscode-export",
        "capture_adapter_version": "0.2.0",
        "provider": "github-copilot-chat",
        "surface": "vscode",
        "exported_at": "2026-04-21T21:00:00Z",
        "session": {
            "session_id": "session-123",
            "started_at": "2026-04-21T20:55:00Z",
            "completed_at": "2026-04-21T21:00:00Z",
            "title": "Investigate webhook plugin support",
            "summary": "Planned a dedicated session webhook plugin.",
            "conversation_url": "https://github.com/copilot/chat/sessions/session-123",
            "topics": ["waygate", "webhooks", "waygate"],
            "tags": ["copilot", "planning", "copilot"],
            "workspace": {
                "workspace_name": "waygate",
                "workspace_root": "/home/buck/src/voidrot/waygate",
                "active_file": "plugins/webhook-generic/pyproject.toml",
                "attached_paths": ["docs/design/runtime-and-plugins.md"],
            },
            "repository": {
                "repository_name": "waygate",
                "repository_url": "https://github.com/voidrot/waygate",
                "branch": "main",
                "commit_sha": "abc123",
                "dirty_worktree": True,
            },
            "messages": [
                {
                    "message_id": "msg-1",
                    "turn_index": 0,
                    "role": "user",
                    "created_at": "2026-04-21T20:55:00Z",
                    "content": "Investigate and plan what is needed.",
                },
                {
                    "message_id": "msg-2",
                    "turn_index": 1,
                    "role": "assistant",
                    "created_at": "2026-04-21T20:56:00Z",
                    "content": "The current plugin seam is sufficient.",
                    "participant": "github-copilot",
                    "tool_calls": [
                        {
                            "tool_name": "grep_search",
                            "call_id": "tool-1",
                            "status": "completed",
                            "input_summary": "Search for webhook plugin classes",
                            "output_summary": "Found generic webhook plugin",
                        }
                    ],
                },
            ],
        },
    }


def _sign(secret: str, body: bytes, timestamp: int | None = None) -> dict[str, str]:
    timestamp_value = int(time.time()) if timestamp is None else timestamp
    digest = hmac.new(
        secret.encode("utf-8"),
        str(timestamp_value).encode("utf-8") + b"." + body,
        hashlib.sha256,
    ).hexdigest()
    return {
        "X-Waygate-Timestamp": str(timestamp_value),
        "X-Waygate-Signature": f"sha256={digest}",
    }


def test_plugin_registers_webhook_hook() -> None:
    assert (
        AgentSessionWebhookPlugin.waygate_webhook_plugin() is AgentSessionWebhookPlugin
    )


def test_plugin_registers_config_hook() -> None:
    registration = AgentSessionWebhookPlugin.waygate_plugin_config()

    assert registration.name == "agent-session"
    assert registration.config is AgentSessionWebhookConfig


def test_openapi_payload_schema_declares_agent_session_payload() -> None:
    plugin = AgentSessionWebhookPlugin(
        config=AgentSessionWebhookConfig(allow_unsigned=True)
    )

    assert plugin.openapi_payload_schema is AgentSessionWebhookPayload


def test_unsigned_requests_are_rejected_by_default() -> None:
    plugin = AgentSessionWebhookPlugin()

    with pytest.raises(WebhookVerificationError, match="require signing"):
        asyncio.run(plugin.verify_webhook_request({}, b"{}"))


def test_allow_unsigned_permits_local_requests() -> None:
    plugin = AgentSessionWebhookPlugin(
        config=AgentSessionWebhookConfig(allow_unsigned=True)
    )

    asyncio.run(plugin.verify_webhook_request({}, b"{}"))


def test_blank_signing_secret_is_rejected() -> None:
    with pytest.raises(ValidationError, match="signing_secret must not be blank"):
        AgentSessionWebhookConfig(signing_secret="   ")


def test_signed_requests_are_verified() -> None:
    plugin = AgentSessionWebhookPlugin(
        config=AgentSessionWebhookConfig(signing_secret="top-secret")
    )
    body = json.dumps(_payload()).encode("utf-8")
    headers = _sign("top-secret", body)

    asyncio.run(plugin.verify_webhook_request(headers, body))


def test_signed_requests_reject_bad_signature() -> None:
    plugin = AgentSessionWebhookPlugin(
        config=AgentSessionWebhookConfig(signing_secret="top-secret")
    )
    body = json.dumps(_payload()).encode("utf-8")
    headers = {
        "X-Waygate-Timestamp": str(int(time.time())),
        "X-Waygate-Signature": "sha256=deadbeef",
    }

    with pytest.raises(WebhookVerificationError, match="verification failed"):
        asyncio.run(plugin.verify_webhook_request(headers, body))


def test_signed_requests_reject_stale_timestamp() -> None:
    plugin = AgentSessionWebhookPlugin(
        config=AgentSessionWebhookConfig(
            signing_secret="top-secret",
            max_timestamp_skew_seconds=5,
        )
    )
    body = json.dumps(_payload()).encode("utf-8")
    headers = _sign("top-secret", body, timestamp=int(time.time()) - 60)

    with pytest.raises(WebhookVerificationError, match="replay window"):
        asyncio.run(plugin.verify_webhook_request(headers, body))


def test_handle_webhook_creates_one_internal_raw_document() -> None:
    plugin = AgentSessionWebhookPlugin(
        config=AgentSessionWebhookConfig(allow_unsigned=True)
    )

    documents = asyncio.run(plugin.handle_webhook(_payload()))

    assert len(documents) == 1
    document = documents[0]
    assert document.source_type == "agent-session"
    assert document.source_id == "session-123"
    assert document.source_uri == "https://github.com/copilot/chat/sessions/session-123"
    assert document.source_hash is not None
    assert document.timestamp.isoformat() == "2026-04-21T21:00:00+00:00"
    assert document.topics == ["waygate", "webhooks"]
    assert document.tags == [
        "copilot",
        "planning",
        "agent-session",
        "provider:github-copilot-chat",
        "surface:vscode",
        "adapter:vscode-export",
    ]
    assert document.visibility is Visibility.INTERNAL
    assert document.source_metadata is not None
    assert document.source_metadata.model_dump()["kind"] == "agent-session"
    assert document.source_metadata.model_dump()["session_id"] == "session-123"

    stored_payload = json.loads(document.content)
    assert stored_payload["provider"] == "github-copilot-chat"
    assert (
        stored_payload["session"]["messages"][1]["tool_calls"][0]["tool_name"]
        == "grep_search"
    )


def test_handle_webhook_uses_synthetic_uri_when_conversation_url_missing() -> None:
    plugin = AgentSessionWebhookPlugin(
        config=AgentSessionWebhookConfig(allow_unsigned=True)
    )
    payload = _payload()
    del payload["session"]["conversation_url"]

    documents = asyncio.run(plugin.handle_webhook(payload))

    assert documents[0].source_uri == "agent-session://github-copilot-chat/session-123"


def test_handle_webhook_rejects_invalid_payload() -> None:
    plugin = AgentSessionWebhookPlugin(
        config=AgentSessionWebhookConfig(allow_unsigned=True)
    )

    with pytest.raises(ValueError, match="Invalid agent-session payload"):
        asyncio.run(plugin.handle_webhook({"session": {}}))


def test_build_workflow_trigger_uses_draft_ready_with_session_metadata() -> None:
    plugin = AgentSessionWebhookPlugin(
        config=AgentSessionWebhookConfig(allow_unsigned=True)
    )
    payload = _payload()

    trigger = plugin.build_workflow_trigger(payload, ["file://raw/session-123.txt"])

    assert trigger == WorkflowTriggerMessage(
        event_type="draft.ready",
        source="waygate-api.webhooks.agent-session",
        document_paths=["file://raw/session-123.txt"],
        idempotency_key="github-copilot-chat:session-123",
        metadata={
            "session_id": "session-123",
            "provider": "github-copilot-chat",
            "surface": "vscode",
            "capture_adapter": "vscode-export",
            "schema_version": "v1",
        },
    )
