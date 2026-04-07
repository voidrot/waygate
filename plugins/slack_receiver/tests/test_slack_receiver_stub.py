import pytest
from importlib import import_module

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
