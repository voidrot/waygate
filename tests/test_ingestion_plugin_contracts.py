import json
from importlib import import_module
from typing import Any

import pytest
from waygate_core.plugin_base import IngestionPlugin


def _assert_canonical_document_shape(doc) -> None:
    assert doc.source_type
    assert doc.source_id
    assert doc.doc_id
    assert doc.content is not None
    assert doc.timestamp.tzinfo is not None
    assert doc.source_hash


PLUGIN_MATRIX = [
    {
        "plugin_path": "waygate_plugin_github_receiver.github_receiver",
        "class_name": "GitHubReceiver",
        "source_type": "github",
        "supports_poll": True,
        "supports_webhook": True,
        "supports_listen": False,
        "expects_typed_metadata": True,
    },
    {
        "plugin_path": "waygate_plugin_slack_receiver.slack_receiver",
        "class_name": "SlackReceiver",
        "source_type": "slack",
        "supports_poll": True,
        "supports_webhook": True,
        "supports_listen": True,
        "expects_typed_metadata": True,
    },
    {
        "plugin_path": "waygate_plugin_generic_webhook.webhook_receiver",
        "class_name": "WebhookReceiver",
        "source_type": "generic_webhook",
        "supports_poll": False,
        "supports_webhook": True,
        "supports_listen": False,
        "expects_typed_metadata": False,
    },
    {
        "plugin_path": "waygate_plugin_linkwarden_receiver.webhook_receiver",
        "class_name": "LinkwardenReceiver",
        "source_type": "web",
        "supports_poll": True,
        "supports_webhook": False,
        "supports_listen": False,
        "expects_typed_metadata": True,
    },
]


def _make_webhook_payload(plugin_class: str) -> dict[str, Any]:
    if plugin_class == "GitHubReceiver":
        return {
            "event": "issue_comment",
            "action": "created",
            "repository": {"full_name": "voidrot/waygate"},
            "comment": {
                "id": 1,
                "body": "hello",
                "created_at": "2026-04-06T10:00:00Z",
            },
        }
    if plugin_class == "SlackReceiver":
        return {
            "event_id": "Ev123",
            "event": {
                "type": "message",
                "channel": "C123",
                "user": "U1",
                "text": "hello",
                "ts": "1712400000.123",
            },
        }
    if plugin_class == "LinkwardenReceiver":
        return {
            "id": "42",
            "url": "https://example.com/notes/42",
            "title": "Clip",
            "description": "hello",
            "tags": ["research"],
            "createdAt": "2026-04-06T10:00:00Z",
        }
    return {
        "source_id": "event-1",
        "content": "hello",
        "timestamp": "2026-04-06T10:00:00Z",
    }


def _prepare_poll_fixture(case: dict[str, Any], tmp_path, monkeypatch) -> None:
    if case["class_name"] == "GitHubReceiver":
        snapshot = {
            "repository": {
                "full_name": "voidrot/waygate",
                "html_url": "https://github.com/voidrot/waygate",
                "owner": {"login": "voidrot"},
            },
            "ref": "refs/heads/main",
            "commit_sha": "deadbeef",
            "files": [{"path": "README.md", "content": "# WayGate"}],
        }
        (tmp_path / "snapshot.json").write_text(json.dumps(snapshot), encoding="utf-8")
        monkeypatch.setenv("GITHUB_EXPORT_PATH", str(tmp_path))
    elif case["class_name"] == "SlackReceiver":
        export = {
            "channel": "C111",
            "messages": [{"type": "message", "text": "hello", "ts": "1712400000.123"}],
        }
        (tmp_path / "export.json").write_text(json.dumps(export), encoding="utf-8")
        monkeypatch.setenv("SLACK_EXPORT_PATH", str(tmp_path))
    elif case["class_name"] == "LinkwardenReceiver":
        monkeypatch.setenv("LINKWARDEN_BASE_URL", "https://example.linkwarden")
        monkeypatch.setenv("LINKWARDEN_TOKEN", "token")
        page = {
            "data": {
                "links": [
                    {
                        "id": 42,
                        "url": "https://example.com/notes/42",
                        "name": "Clip",
                        "description": "hello",
                        "tags": [{"name": "research"}],
                        "createdAt": "2026-04-06T10:00:00Z",
                    }
                ],
                "nextCursor": None,
            }
        }

        class _MockResponse:
            def __init__(self, payload: dict[str, Any]) -> None:
                self._payload = payload

            def read(self) -> bytes:
                return json.dumps(self._payload).encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        monkeypatch.setattr(
            "waygate_plugin_linkwarden_receiver.webhook_receiver.urlopen",
            lambda _req: _MockResponse(page),
        )


def _prepare_listen_fixture(case: dict[str, Any], plugin: Any) -> None:
    if case["class_name"] == "SlackReceiver":
        plugin._listen_events = [
            {
                "event_id": "Ev123",
                "event": {
                    "type": "message",
                    "channel": "C123",
                    "user": "U1",
                    "text": "hello",
                    "ts": "1712400000.123",
                },
            }
        ]


def test_plugins_inherit_ingestion_base_contract() -> None:
    plugins = [
        getattr(import_module(case["plugin_path"]), case["class_name"])()
        for case in PLUGIN_MATRIX
    ]

    for plugin in plugins:
        assert isinstance(plugin, IngestionPlugin)


@pytest.mark.parametrize("case", PLUGIN_MATRIX)
def test_webhook_contract_normalizes_to_raw_document(case: dict[str, Any]) -> None:
    plugin = getattr(import_module(case["plugin_path"]), case["class_name"])()

    if not case["supports_webhook"]:
        with pytest.raises(NotImplementedError):
            plugin.handle_webhook(_make_webhook_payload(case["class_name"]))
        return

    docs = plugin.handle_webhook(_make_webhook_payload(case["class_name"]))
    assert docs
    doc = docs[0]
    _assert_canonical_document_shape(doc)
    assert doc.source_type == case["source_type"]
    if case["expects_typed_metadata"]:
        assert doc.source_metadata is not None


@pytest.mark.parametrize("case", PLUGIN_MATRIX)
def test_poll_contract_behavior_by_plugin(
    tmp_path,
    monkeypatch,
    case: dict[str, Any],
) -> None:
    plugin = getattr(import_module(case["plugin_path"]), case["class_name"])()
    _prepare_poll_fixture(case, tmp_path, monkeypatch)

    if not case["supports_poll"]:
        with pytest.raises(NotImplementedError):
            plugin.poll()
        return

    docs = plugin.poll()
    assert docs
    _assert_canonical_document_shape(docs[0])
    assert docs[0].source_type == case["source_type"]


@pytest.mark.anyio
@pytest.mark.parametrize("case", PLUGIN_MATRIX)
async def test_listen_contract_behavior_by_plugin(
    case: dict[str, Any],
) -> None:
    plugin = getattr(import_module(case["plugin_path"]), case["class_name"])()

    captured = []

    async def _callback(docs):
        captured.extend(docs)

    _prepare_listen_fixture(case, plugin)

    if not case["supports_listen"]:
        with pytest.raises(NotImplementedError):
            await plugin.listen(_callback)
        return

    await plugin.listen(_callback)
    assert captured
    _assert_canonical_document_shape(captured[0])
