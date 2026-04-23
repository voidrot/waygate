import asyncio

import httpx

from waygate_core.plugin import DispatchErrorKind, WorkflowTriggerMessage
from waygate_plugin_communication_http.plugin import (
    CommunicationHttpConfig,
    CommunicationHttpPlugin,
    CommunicationHttpWorkerTransport,
)


class FakeResponse:
    def __init__(
        self, *, payload=None, status_error: httpx.HTTPError | None = None
    ) -> None:
        self._payload = payload if payload is not None else {}
        self._status_error = status_error
        self.content = b"{}" if payload is not None else b""

    def raise_for_status(self) -> None:
        if self._status_error is not None:
            raise self._status_error

    def json(self):
        return self._payload


class FakeAsyncClient:
    def __init__(self, response: FakeResponse | list[FakeResponse]) -> None:
        self._responses = response if isinstance(response, list) else [response]

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def post(self, url: str, headers: dict[str, str], json: dict):
        return self._responses.pop(0)


def test_submit_workflow_trigger_returns_accepted_on_success(monkeypatch) -> None:
    response = FakeResponse(payload={"message_id": "worker-123"})
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda timeout: FakeAsyncClient(response),
    )

    plugin = CommunicationHttpPlugin()
    result = asyncio.run(
        plugin.submit_workflow_trigger(
            WorkflowTriggerMessage(
                event_type="draft.ready",
                source="test",
                document_paths=["raw/one.txt"],
            )
        )
    )

    assert result.accepted is True
    assert result.transport_message_id == "worker-123"
    assert result.error_kind is None


def test_submit_workflow_trigger_maps_http_errors_to_not_accepted(monkeypatch) -> None:
    request = httpx.Request("POST", "http://localhost/workflows/trigger")
    status_error = httpx.HTTPStatusError(
        message="upstream failed",
        request=request,
        response=httpx.Response(status_code=503, request=request),
    )
    response = FakeResponse(status_error=status_error)
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda timeout: FakeAsyncClient(response),
    )

    plugin = CommunicationHttpPlugin()
    result = asyncio.run(
        plugin.submit_workflow_trigger(
            WorkflowTriggerMessage(
                event_type="draft.ready",
                source="test",
                document_paths=["raw/one.txt"],
            )
        )
    )

    assert result.accepted is False
    assert result.error_kind == DispatchErrorKind.TRANSIENT


def test_submit_workflow_trigger_returns_config_error_for_empty_endpoint() -> None:
    plugin = CommunicationHttpPlugin(config=CommunicationHttpConfig(endpoint=""))

    result = asyncio.run(
        plugin.submit_workflow_trigger(
            WorkflowTriggerMessage(
                event_type="draft.ready",
                source="test",
                document_paths=["raw/one.txt"],
            )
        )
    )

    assert result.accepted is False
    assert result.error_kind == DispatchErrorKind.CONFIG


def test_submit_workflow_trigger_retries_transient_http_status(monkeypatch) -> None:
    request = httpx.Request("POST", "http://localhost/workflows/trigger")
    first = FakeResponse(
        status_error=httpx.HTTPStatusError(
            message="temporary outage",
            request=request,
            response=httpx.Response(status_code=503, request=request),
        )
    )
    second = FakeResponse(payload={"message_id": "retry-success"})

    client = FakeAsyncClient([first, second])
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda timeout: client,
    )

    plugin = CommunicationHttpPlugin(
        config=CommunicationHttpConfig(max_retries=1, retry_backoff_seconds=0.0001)
    )
    result = asyncio.run(
        plugin.submit_workflow_trigger(
            WorkflowTriggerMessage(
                event_type="draft.ready",
                source="test",
                document_paths=["raw/one.txt"],
            )
        )
    )

    assert result.accepted is True
    assert result.transport_message_id == "retry-success"


def test_http_plugin_registers_worker_transport_companion() -> None:
    worker_transport = CommunicationHttpPlugin.waygate_worker_transport_plugin()

    assert worker_transport is CommunicationHttpWorkerTransport
