import pytest
from importlib import import_module
import hashlib
import hmac
import json

from waygate_core.plugin_base import WebhookVerificationError

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


def test_github_receiver_invalid_timestamp_falls_back_to_now() -> None:
    receiver = GitHubReceiver()

    payload = {
        "event": "issue_comment",
        "action": "created",
        "repository": {"full_name": "voidrot/waygate"},
        "comment": {
            "id": 9002,
            "body": "Timestamp fallback",
            "created_at": "not-a-timestamp",
        },
    }

    docs = receiver.handle_webhook(payload)

    assert len(docs) == 1
    assert docs[0].timestamp.tzinfo is not None


def test_github_metadata_model_defaults() -> None:
    metadata = GitHubSourceMetadata(repo_name="voidrot/waygate")

    assert metadata.kind == "github"
    assert metadata.repo_name == "voidrot/waygate"


def test_github_receiver_poll_ingests_snapshot_exports(tmp_path, monkeypatch) -> None:
    receiver = GitHubReceiver()

    snapshot = {
        "repository": {
            "full_name": "voidrot/waygate",
            "html_url": "https://github.com/voidrot/waygate",
            "owner": {"login": "voidrot"},
        },
        "ref": "refs/heads/main",
        "commit_sha": "deadbeef",
        "files": [
            {
                "path": "README.md",
                "content": "# WayGate",
                "language": "Markdown",
                "sha": "sha-readme",
            },
            {
                "path": "apps/compiler/src/compiler/graph.py",
                "content": "print('hello')",
                "language": "Python",
                "sha": "sha-graph",
            },
        ],
    }
    snapshot_path = tmp_path / "snapshot.json"
    snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")

    monkeypatch.setenv("GITHUB_EXPORT_PATH", str(tmp_path))
    docs = receiver.poll()

    assert len(docs) == 2
    for doc in docs:
        assert doc.source_type == "github"
        assert doc.source_hash is not None
        assert doc.source_metadata is not None
        assert doc.source_metadata.kind == "github"
        assert doc.source_metadata.repo_name == "voidrot/waygate"
        assert doc.source_metadata.branch == "main"
        assert doc.source_metadata.commit_sha == "deadbeef"
        assert doc.source_metadata.owner == "voidrot"
        assert "snapshot" in doc.tags


def test_github_receiver_parses_issue_payload_with_labels_and_assignees() -> None:
    receiver = GitHubReceiver()

    payload = {
        "event": "issues",
        "action": "opened",
        "repository": {"full_name": "voidrot/waygate"},
        "issue": {
            "id": 100,
            "number": 9,
            "title": "Receiver bug",
            "body": "Webhook processing fails.",
            "labels": [{"name": "bug"}, {"name": "receiver"}],
            "assignees": [{"login": "buck"}],
            "created_at": "2026-04-06T12:00:00Z",
        },
    }

    docs = receiver.handle_webhook(payload)

    assert "GitHub issue 9 opened: Receiver bug" in docs[0].content
    assert "Labels: bug, receiver" in docs[0].content
    assert "Assignees: buck" in docs[0].content


def test_github_receiver_parses_pull_request_review_payload() -> None:
    receiver = GitHubReceiver()

    payload = {
        "event": "pull_request_review",
        "action": "submitted",
        "repository": {"full_name": "voidrot/waygate"},
        "pull_request": {
            "id": 42,
            "number": 42,
            "title": "Improve receiver",
            "html_url": "https://github.com/voidrot/waygate/pull/42",
        },
        "review": {
            "id": 77,
            "state": "approved",
            "body": "Looks solid.",
            "submitted_at": "2026-04-06T12:00:00Z",
        },
    }

    docs = receiver.handle_webhook(payload)

    assert docs[0].source_id == "77"
    assert "GitHub PR review for #42 submitted: Improve receiver" in docs[0].content
    assert "Review state: approved" in docs[0].content
    assert "Looks solid." in docs[0].content


def test_github_receiver_parses_push_payload_into_commit_batch_summary() -> None:
    receiver = GitHubReceiver()

    payload = {
        "event": "push",
        "ref": "refs/heads/main",
        "after": "abc1234567",
        "repository": {"full_name": "voidrot/waygate"},
        "commits": [
            {
                "id": "abc1234567",
                "message": "Add webhook validation",
                "added": ["apps/receiver/src/receiver/api/webhooks.py"],
                "modified": ["README.md"],
                "removed": [],
            },
            {
                "id": "def7654321",
                "message": "Add tests",
                "added": [],
                "modified": ["apps/receiver/tests/test_webhooks_api.py"],
                "removed": [],
            },
        ],
    }

    docs = receiver.handle_webhook(payload)

    assert "GitHub push to voidrot/waygate on main" in docs[0].content
    assert "Commit count: 2" in docs[0].content
    assert "- abc1234 Add webhook validation" in docs[0].content
    assert "- def7654 Add tests" in docs[0].content
    assert "Changed files:" in docs[0].content
    assert "apps/receiver/src/receiver/api/webhooks.py" in docs[0].content


def test_github_receiver_rejects_invalid_signature(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "secret")
    receiver = GitHubReceiver()

    with pytest.raises(
        WebhookVerificationError, match="Invalid GitHub webhook signature"
    ):
        receiver.verify_webhook_request(
            {"x-hub-signature-256": "sha256=bad"},
            b"{}",
        )


def test_github_receiver_accepts_valid_signature(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "secret")
    receiver = GitHubReceiver()

    body = b'{"event":"issues"}'
    signature = "sha256=" + hmac.new(b"secret", body, hashlib.sha256).hexdigest()

    receiver.verify_webhook_request(
        {"x-hub-signature-256": signature},
        body,
    )


def test_github_receiver_prepares_payload_from_headers() -> None:
    receiver = GitHubReceiver()

    payload = receiver.prepare_webhook_payload(
        {"action": "opened"},
        {
            "x-github-event": "issues",
            "x-github-delivery": "delivery-1",
        },
    )

    assert payload["event"] == "issues"
    assert payload["delivery_id"] == "delivery-1"
