import asyncio
from types import SimpleNamespace

import pytest

from waygate_api import clients
from waygate_core.plugin import (
    CommunicationClientResolutionError,
    WorkflowDispatchResult,
    WorkflowTriggerMessage,
)


class FakeCommunicationClient:
    def __init__(self) -> None:
        self.messages = []

    async def submit_workflow_trigger(self, message):
        self.messages.append(message)
        return WorkflowDispatchResult(accepted=True, transport_message_id="msg-1")


def _make_app_context(preferred: str, client_map: dict[str, object]):
    return SimpleNamespace(
        config=SimpleNamespace(
            core=SimpleNamespace(communication_plugin_name=preferred)
        ),
        plugins=SimpleNamespace(communication=client_map),
    )


def test_resolve_communication_client_uses_preferred(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preferred = FakeCommunicationClient()
    fallback = FakeCommunicationClient()
    context = _make_app_context(
        "preferred", {"preferred": preferred, "fallback": fallback}
    )
    monkeypatch.setattr(clients, "get_app_context", lambda: context)

    resolved = clients._resolve_communication_client()

    assert resolved is preferred


def test_resolve_communication_client_raises_when_preferred_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fallback = FakeCommunicationClient()
    context = _make_app_context("missing", {"fallback": fallback})
    monkeypatch.setattr(clients, "get_app_context", lambda: context)

    with pytest.raises(CommunicationClientResolutionError, match="unavailable"):
        clients._resolve_communication_client()


def test_resolve_communication_client_raises_when_none_installed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _make_app_context("preferred", {})
    monkeypatch.setattr(clients, "get_app_context", lambda: context)

    with pytest.raises(RuntimeError, match="No communication plugins"):
        clients._resolve_communication_client()


def test_send_draft_message_submits_expected_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    communication_client = FakeCommunicationClient()
    context = _make_app_context("preferred", {"preferred": communication_client})
    monkeypatch.setattr(clients, "get_app_context", lambda: context)

    result = asyncio.run(clients.send_draft_message(["raw/a.txt", "raw/b.txt"]))

    assert result.accepted is True
    assert len(communication_client.messages) == 1
    message = communication_client.messages[0]
    assert message.event_type == "draft.ready"
    assert message.source == "waygate-api.webhooks"
    assert message.document_paths == ["raw/a.txt", "raw/b.txt"]


def test_send_draft_message_short_circuits_empty_document_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    communication_client = FakeCommunicationClient()
    context = _make_app_context("preferred", {"preferred": communication_client})
    monkeypatch.setattr(clients, "get_app_context", lambda: context)

    result = asyncio.run(clients.send_draft_message([]))

    assert result.accepted is True
    assert result.detail == "No document paths supplied"
    assert communication_client.messages == []


def test_send_workflow_message_submits_custom_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    communication_client = FakeCommunicationClient()
    context = _make_app_context("preferred", {"preferred": communication_client})
    monkeypatch.setattr(clients, "get_app_context", lambda: context)

    message = WorkflowTriggerMessage(
        event_type="draft.ready",
        source="waygate-api.webhooks.agent-session",
        document_paths=["file://raw/session-123.txt"],
        idempotency_key="github-copilot-chat:session-123",
        metadata={"session_id": "session-123"},
    )

    result = asyncio.run(clients.send_workflow_message(message))

    assert result.accepted is True
    assert communication_client.messages == [message]


def test_send_workflow_message_submits_metadata_only_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    communication_client = FakeCommunicationClient()
    context = _make_app_context("preferred", {"preferred": communication_client})
    monkeypatch.setattr(clients, "get_app_context", lambda: context)

    message = WorkflowTriggerMessage(
        event_type="cron.tick",
        source="waygate-scheduler.cron.example",
        document_paths=[],
        metadata={"schedule": "*/5 * * * *"},
    )

    result = asyncio.run(clients.send_workflow_message(message))

    assert result.accepted is True
    assert communication_client.messages == [message]
