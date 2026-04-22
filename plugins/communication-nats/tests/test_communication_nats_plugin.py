import asyncio
from types import SimpleNamespace

from waygate_core.plugin import DispatchErrorKind, WorkflowTriggerMessage
from waygate_plugin_communication_nats.plugin import (
    CommunicationNatsConfig,
    CommunicationNatsPlugin,
)


class FakeAck:
    def __init__(
        self,
        *,
        stream: str = "WAYGATE_WORKFLOW",
        seq: int = 42,
        duplicate: bool = False,
    ) -> None:
        self.stream = stream
        self.seq = seq
        self.duplicate = duplicate


class FakeJetStream:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.publish_result = FakeAck()
        self.raise_error: Exception | None = None
        self.added = []
        self.updated = []
        self.raise_missing = False
        self.subjects = ["waygate.workflow.draft", "waygate.workflow.cron"]

    async def publish(self, subject: str, payload: bytes, **kwargs):
        if self.raise_error is not None:
            raise self.raise_error
        self.calls.append({"subject": subject, "payload": payload, **kwargs})
        return self.publish_result

    async def stream_info(self, name: str):
        if self.raise_missing:
            raise type("FakeApiError", (Exception,), {"code": 404})("missing stream")
        return SimpleNamespace(config=SimpleNamespace(subjects=self.subjects))

    async def add_stream(self, *, config) -> None:
        self.added.append(config)

    async def update_stream(self, *, config) -> None:
        self.updated.append(config)


class FakeConnection:
    def __init__(self, jetstream: FakeJetStream) -> None:
        self._jetstream = jetstream
        self.drained = False
        self.closed = False

    def jetstream(self, *, timeout: float):
        return self._jetstream

    async def drain(self) -> None:
        self.drained = True

    async def close(self) -> None:
        self.closed = True


def test_submit_workflow_trigger_publishes_to_jetstream(monkeypatch) -> None:
    jetstream = FakeJetStream()
    connection = FakeConnection(jetstream)

    async def _connect(**kwargs):
        return connection

    monkeypatch.setattr(
        "waygate_plugin_communication_nats.plugin.nats.connect",
        _connect,
    )

    plugin = CommunicationNatsPlugin(CommunicationNatsConfig())
    result = asyncio.run(
        plugin.submit_workflow_trigger(
            WorkflowTriggerMessage(
                event_type="draft.ready",
                source="test",
                document_paths=["file://raw/one.txt"],
                idempotency_key="abc-123",
            )
        )
    )

    assert result.accepted is True
    assert result.transport_message_id == "draft.ready:abc-123"
    assert jetstream.calls[0]["subject"] == "waygate.workflow.draft"
    assert jetstream.calls[0]["stream"] == "WAYGATE_WORKFLOW"
    assert jetstream.calls[0]["headers"] == {"Nats-Msg-Id": "draft.ready:abc-123"}
    assert connection.drained is True


def test_submit_workflow_trigger_returns_validation_error_for_missing_documents() -> (
    None
):
    plugin = CommunicationNatsPlugin()

    result = asyncio.run(
        plugin.submit_workflow_trigger(
            WorkflowTriggerMessage(
                event_type="draft.ready",
                source="test",
                document_paths=[],
            )
        )
    )

    assert result.accepted is False
    assert result.error_kind == DispatchErrorKind.VALIDATION


def test_submit_workflow_trigger_marks_duplicate_publish_as_accepted(
    monkeypatch,
) -> None:
    jetstream = FakeJetStream()
    jetstream.publish_result = FakeAck(duplicate=True)
    connection = FakeConnection(jetstream)

    async def _connect(**kwargs):
        return connection

    monkeypatch.setattr(
        "waygate_plugin_communication_nats.plugin.nats.connect",
        _connect,
    )

    plugin = CommunicationNatsPlugin(CommunicationNatsConfig())
    result = asyncio.run(
        plugin.submit_workflow_trigger(
            WorkflowTriggerMessage(
                event_type="draft.ready",
                source="test",
                document_paths=["file://raw/one.txt"],
                idempotency_key="abc-123",
            )
        )
    )

    assert result.accepted is True
    assert "already present" in str(result.detail)


def test_submit_workflow_trigger_maps_config_error(monkeypatch) -> None:
    jetstream = FakeJetStream()
    jetstream.raise_error = type("FakeApiError", (Exception,), {"code": 404})(
        "missing stream"
    )
    connection = FakeConnection(jetstream)

    async def _connect(**kwargs):
        return connection

    monkeypatch.setattr(
        "waygate_plugin_communication_nats.plugin.nats.connect",
        _connect,
    )

    plugin = CommunicationNatsPlugin(CommunicationNatsConfig())
    result = asyncio.run(
        plugin.submit_workflow_trigger(
            WorkflowTriggerMessage(
                event_type="draft.ready",
                source="test",
                document_paths=["file://raw/one.txt"],
            )
        )
    )

    assert result.accepted is False
    assert result.error_kind == DispatchErrorKind.CONFIG


def test_submit_workflow_trigger_maps_transient_connect_error(monkeypatch) -> None:
    class FakeConnectError(Exception):
        pass

    async def _connect(**kwargs):
        raise FakeConnectError("offline")

    monkeypatch.setattr(
        "waygate_plugin_communication_nats.plugin.nats.connect",
        _connect,
    )
    monkeypatch.setattr(
        "waygate_plugin_communication_nats.plugin.NoServersError",
        FakeConnectError,
    )

    plugin = CommunicationNatsPlugin(CommunicationNatsConfig())
    result = asyncio.run(
        plugin.submit_workflow_trigger(
            WorkflowTriggerMessage(
                event_type="draft.ready",
                source="test",
                document_paths=["file://raw/one.txt"],
            )
        )
    )

    assert result.accepted is False
    assert result.error_kind == DispatchErrorKind.TRANSIENT


def test_config_accepts_comma_delimited_servers() -> None:
    config = CommunicationNatsConfig(servers="nats://one:4222,nats://two:4222")

    assert config.servers == ["nats://one:4222", "nats://two:4222"]


def test_submit_workflow_trigger_creates_stream_when_missing(monkeypatch) -> None:
    jetstream = FakeJetStream()
    jetstream.raise_missing = True
    connection = FakeConnection(jetstream)

    async def _connect(**kwargs):
        return connection

    monkeypatch.setattr(
        "waygate_plugin_communication_nats.plugin.nats.connect",
        _connect,
    )

    plugin = CommunicationNatsPlugin(CommunicationNatsConfig())
    result = asyncio.run(
        plugin.submit_workflow_trigger(
            WorkflowTriggerMessage(
                event_type="draft.ready",
                source="test",
                document_paths=["file://raw/one.txt"],
            )
        )
    )

    assert result.accepted is True
    assert jetstream.added[0].name == "WAYGATE_WORKFLOW"
    assert jetstream.calls[0]["stream"] == "WAYGATE_WORKFLOW"


def test_submit_workflow_trigger_routes_ready_integrate_to_draft_subject(
    monkeypatch,
) -> None:
    jetstream = FakeJetStream()
    connection = FakeConnection(jetstream)

    async def _connect(**kwargs):
        return connection

    monkeypatch.setattr(
        "waygate_plugin_communication_nats.plugin.nats.connect",
        _connect,
    )

    plugin = CommunicationNatsPlugin(CommunicationNatsConfig())
    result = asyncio.run(
        plugin.submit_workflow_trigger(
            WorkflowTriggerMessage(
                event_type="ready.integrate",
                source="test",
                document_paths=["file://compiled/compiled-abc.md"],
                idempotency_key="compiled-abc",
            )
        )
    )

    assert result.accepted is True
    assert result.transport_message_id == "ready.integrate:compiled-abc"
    assert jetstream.calls[0]["subject"] == "waygate.workflow.draft"
