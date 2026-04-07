import pytest
from importlib import import_module

GitHubReceiver = import_module(
    "waygate_plugin_github_receiver.github_receiver"
).GitHubReceiver
GitHubSourceMetadata = import_module(
    "waygate_plugin_github_receiver.metadata"
).GitHubSourceMetadata


def test_github_receiver_stub_identity() -> None:
    receiver = GitHubReceiver()

    assert receiver.plugin_name == "github_receiver"
    assert receiver.poll() == []


def test_github_receiver_raises_for_empty_payload() -> None:
    receiver = GitHubReceiver()

    with pytest.raises(ValueError, match="Webhook body cannot be empty"):
        receiver.handle_webhook({})


def test_github_receiver_parses_pull_request_payload() -> None:
    receiver = GitHubReceiver()

    payload = {
        "event": "pull_request",
        "action": "opened",
        "ref": "refs/heads/main",
        "after": "abc123",
        "repository": {
            "full_name": "voidrot/waygate",
            "html_url": "https://github.com/voidrot/waygate",
            "owner": {"login": "voidrot"},
        },
        "pull_request": {
            "id": 42,
            "title": "Improve receiver",
            "body": "Adds canonical metadata.",
            "html_url": "https://github.com/voidrot/waygate/pull/42",
            "updated_at": "2026-04-06T12:00:00Z",
        },
    }

    docs = receiver.handle_webhook(payload)

    assert len(docs) == 1
    doc = docs[0]
    assert doc.source_type == "github"
    assert doc.source_id == "42"
    assert doc.source_url == "https://github.com/voidrot/waygate/pull/42"
    assert doc.source_hash is not None
    assert "github" in doc.tags
    assert "pull_request" in doc.tags
    assert "opened" in doc.tags
    assert "Improve receiver" in doc.content
    assert doc.source_metadata is not None
    assert doc.source_metadata.kind == "github"
    assert doc.source_metadata.repo_name == "voidrot/waygate"
    assert doc.source_metadata.branch == "main"
    assert doc.source_metadata.commit_sha == "abc123"
    assert doc.source_metadata.owner == "voidrot"


def test_github_receiver_uses_comment_body_when_present() -> None:
    receiver = GitHubReceiver()

    payload = {
        "event": "issue_comment",
        "action": "created",
        "repository": {"full_name": "voidrot/waygate"},
        "comment": {
            "id": 9001,
            "body": "Looks good to me",
            "html_url": "https://github.com/voidrot/waygate/issues/1#issuecomment-9001",
            "created_at": "2026-04-06T10:00:00Z",
        },
    }

    docs = receiver.handle_webhook(payload)
    assert docs[0].content == "Looks good to me"
    assert docs[0].source_url and "issuecomment" in docs[0].source_url


def test_github_metadata_model_defaults() -> None:
    metadata = GitHubSourceMetadata(repo_name="voidrot/waygate")

    assert metadata.kind == "github"
    assert metadata.repo_name == "voidrot/waygate"
