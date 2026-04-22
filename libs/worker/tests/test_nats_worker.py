import asyncio
import json
import time
from types import SimpleNamespace

from nats.errors import TimeoutError as NatsTimeoutError

from waygate_core.plugin import DispatchErrorKind
from waygate_worker.nats import (
    NatsWorkerConfig,
    _ensure_stream,
    _fetch_messages,
    process_jetstream_message,
)


class FakeJetStreamMessage:
    def __init__(self, payload: dict[str, object] | bytes) -> None:
        self.data = (
            payload
            if isinstance(payload, bytes)
            else json.dumps(payload).encode("utf-8")
        )
        self.calls: list[str] = []

    async def ack(self) -> None:
        self.calls.append("ack")

    async def nak(self) -> None:
        self.calls.append("nak")

    async def term(self) -> None:
        self.calls.append("term")

    async def in_progress(self) -> None:
        self.calls.append("in_progress")


def test_process_jetstream_message_acks_completed_payload() -> None:
    message = FakeJetStreamMessage({"event_type": "draft.ready"})

    result = asyncio.run(
        process_jetstream_message(
            message,
            runner=lambda payload: {"status": "completed", "request_key": "abc"},
            heartbeat_interval=0.01,
        )
    )

    assert result["status"] == "completed"
    assert message.calls == ["ack"]


def test_process_jetstream_message_terms_terminal_failure() -> None:
    message = FakeJetStreamMessage({"event_type": "draft.ready"})

    result = asyncio.run(
        process_jetstream_message(
            message,
            runner=lambda payload: {
                "status": "failed",
                "error_kind": DispatchErrorKind.VALIDATION.value,
            },
            heartbeat_interval=0.01,
        )
    )

    assert result["status"] == "failed"
    assert message.calls == ["term"]


def test_process_jetstream_message_naks_transient_exception() -> None:
    message = FakeJetStreamMessage({"event_type": "draft.ready"})

    def _runner(payload: dict[str, object]) -> dict[str, object]:
        raise RuntimeError("boom")

    result = asyncio.run(
        process_jetstream_message(message, runner=_runner, heartbeat_interval=0.01)
    )

    assert result["error_kind"] == DispatchErrorKind.TRANSIENT.value
    assert message.calls == ["nak"]


def test_process_jetstream_message_sends_in_progress_heartbeats() -> None:
    message = FakeJetStreamMessage({"event_type": "draft.ready"})

    def _runner(payload: dict[str, object]) -> dict[str, object]:
        time.sleep(0.03)
        return {"status": "completed"}

    asyncio.run(
        process_jetstream_message(message, runner=_runner, heartbeat_interval=0.01)
    )

    assert "in_progress" in message.calls
    assert message.calls[-1] == "ack"


def test_process_jetstream_message_terms_invalid_json() -> None:
    message = FakeJetStreamMessage(b"not-json")

    result = asyncio.run(process_jetstream_message(message, heartbeat_interval=0.01))

    assert result["error_kind"] == DispatchErrorKind.VALIDATION.value
    assert message.calls == ["term"]


def test_ensure_stream_adds_when_missing() -> None:
    added = []

    class MissingStreamError(Exception):
        def __init__(self) -> None:
            super().__init__("missing")
            self.code = 404

    class FakeJetStream:
        async def stream_info(self, name: str):
            raise MissingStreamError()

        async def add_stream(self, *, config) -> None:
            added.append(config)

    nc = SimpleNamespace(jetstream=lambda timeout: FakeJetStream())

    asyncio.run(_ensure_stream(nc, NatsWorkerConfig()))

    assert added[0].name == "WAYGATE_WORKFLOW"


def test_worker_config_accepts_compose_style_env_strings(monkeypatch) -> None:
    monkeypatch.setenv("WAYGATE_WORKER__SERVERS", "nats://nats:4222")
    monkeypatch.setenv("WAYGATE_WORKER__BACKOFF_SECONDS", "[10, 30, 60]")

    config = NatsWorkerConfig()

    assert config.servers == ["nats://nats:4222"]
    assert config.backoff_seconds == [10.0, 30.0, 60.0]


def test_fetch_messages_returns_empty_on_fetch_timeout(monkeypatch) -> None:
    class FakeSubscription:
        async def fetch(self, **kwargs):
            raise NatsTimeoutError

    result = asyncio.run(_fetch_messages(FakeSubscription(), NatsWorkerConfig()))

    assert result == []
