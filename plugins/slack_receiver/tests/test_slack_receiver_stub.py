import pytest
from importlib import import_module
import hashlib
import hmac
import json
from datetime import UTC, datetime

from waygate_core.plugin_base import WebhookVerificationError

SlackSourceMetadata = import_module(
    "waygate_plugin_slack_receiver.metadata"
).SlackSourceMetadata
SlackReceiver = import_module(
    "waygate_plugin_slack_receiver.slack_receiver"
).SlackReceiver


def test_slack_receiver_stub_identity() -> None:
    receiver = SlackReceiver()

    assert receiver.plugin_name == "slack_receiver"
    assert receiver.poll() == []


def test_slack_receiver_raises_for_empty_payload() -> None:
    receiver = SlackReceiver()

    with pytest.raises(ValueError, match="Webhook body cannot be empty"):
        receiver.handle_webhook({})


def test_slack_receiver_parses_event_callback_payload() -> None:
    receiver = SlackReceiver()

    payload = {
        "type": "event_callback",
        "event_id": "Ev123",
        "event": {
            "type": "message",
            "channel": "C123",
            "user": "U42",
            "text": "Deploy is green",
            "ts": "1712400000.123",
            "thread_ts": "1712400000.000",
            "permalink": "https://workspace.slack.com/archives/C123/p1712400000123",
        },
    }

    docs = receiver.handle_webhook(payload)

    assert len(docs) == 1
    doc = docs[0]
    assert doc.source_type == "slack"
    assert doc.source_id == "Ev123"
    assert doc.content == "Deploy is green"
    assert doc.source_url and "slack.com" in doc.source_url
    assert "slack" in doc.tags
    assert "message" in doc.tags
    assert "C123" in doc.tags
    assert doc.source_hash is not None
    assert doc.source_metadata is not None
    assert doc.source_metadata.kind == "slack"
    assert doc.source_metadata.channel_id == "C123"
    assert doc.source_metadata.thread_ts == "1712400000.000"
    assert doc.source_metadata.participants == ["U42"]
    assert doc.source_metadata.semantic_type == "message"
    assert doc.source_metadata.anchor_id == "1712400000.123"


def test_slack_receiver_parses_flat_payload_shape() -> None:
    receiver = SlackReceiver()

    payload = {
        "type": "message",
        "channel_id": "C999",
        "user_id": "U999",
        "text": "Flat payload",
        "ts": "2026-04-06T10:00:00Z",
    }

    docs = receiver.handle_webhook(payload)
    assert docs[0].content == "Flat payload"
    assert docs[0].source_metadata is not None
    assert docs[0].source_metadata.channel_id == "C999"


def test_slack_receiver_invalid_timestamp_falls_back_to_now() -> None:
    receiver = SlackReceiver()

    payload = {
        "type": "message",
        "channel_id": "C999",
        "user_id": "U999",
        "text": "Bad timestamp",
        "ts": "not-a-timestamp",
    }

    docs = receiver.handle_webhook(payload)

    assert len(docs) == 1
    assert docs[0].timestamp.tzinfo is not None


def test_slack_metadata_model_defaults() -> None:
    metadata = SlackSourceMetadata(channel_id="C123")

    assert metadata.kind == "slack"
    assert metadata.channel_id == "C123"


def test_slack_receiver_poll_ingests_export_messages(tmp_path, monkeypatch) -> None:
    receiver = SlackReceiver()

    export = {
        "channel": "C111",
        "messages": [
            {
                "type": "message",
                "user": "U1",
                "text": "First",
                "ts": "1712400000.123",
            },
            {
                "type": "message",
                "user": "U2",
                "text": "Second",
                "ts": "1712400300.000",
                "thread_ts": "1712400000.123",
            },
        ],
    }
    export_path = tmp_path / "export.json"
    export_path.write_text(json.dumps(export), encoding="utf-8")

    monkeypatch.setenv("SLACK_EXPORT_PATH", str(tmp_path))
    docs = receiver.poll()

    assert len(docs) == 2
    assert docs[0].source_type == "slack"
    assert docs[0].source_metadata is not None
    assert docs[0].source_metadata.channel_id == "C111"


@pytest.mark.anyio
async def test_slack_receiver_listen_emits_normalized_documents() -> None:
    receiver = SlackReceiver()
    receiver._listen_events = [
        {
            "event_id": "Ev-L1",
            "event": {
                "type": "message",
                "channel": "C123",
                "user": "U42",
                "text": "from listen",
                "ts": "1712400000.123",
            },
        }
    ]

    captured = []

    async def _callback(docs):
        captured.extend(docs)

    await receiver.listen(_callback)

    assert len(captured) == 1
    assert captured[0].source_type == "slack"
    assert captured[0].content == "from listen"


def test_slack_receiver_rejects_invalid_signature(monkeypatch) -> None:
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "secret")
    receiver = SlackReceiver()

    with pytest.raises(WebhookVerificationError, match="Invalid Slack webhook signature"):
        receiver.verify_webhook_request(
            {
                "x-slack-request-timestamp": str(int(datetime.now(UTC).timestamp())),
                "x-slack-signature": "v0=bad",
            },
            b"{}",
        )


def test_slack_receiver_accepts_valid_signature(monkeypatch) -> None:
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "secret")
    receiver = SlackReceiver()

    body = b'{"type":"event_callback"}'
    timestamp = str(int(datetime.now(UTC).timestamp()))
    basestring = f"v0:{timestamp}:".encode("utf-8") + body
    signature = "v0=" + hmac.new(b"secret", basestring, hashlib.sha256).hexdigest()

    receiver.verify_webhook_request(
        {
            "x-slack-request-timestamp": timestamp,
            "x-slack-signature": signature,
        },
        body,
    )


def test_slack_receiver_rejects_stale_timestamp(monkeypatch) -> None:
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "secret")
    receiver = SlackReceiver()

    with pytest.raises(WebhookVerificationError, match="Stale Slack webhook request timestamp"):
        receiver.verify_webhook_request(
            {
                "x-slack-request-timestamp": str(int(datetime(2020, 1, 1, tzinfo=UTC).timestamp())),
                "x-slack-signature": "v0=deadbeef",
            },
            b"{}",
        )
