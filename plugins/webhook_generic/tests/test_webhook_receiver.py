from waygate_plugin_generic_webhook.webhook_receiver import WebhookReceiver


def test_handle_webhook_populates_generic_canonical_metadata() -> None:
    receiver = WebhookReceiver()

    docs = receiver.handle_webhook(
        {
            "source_id": "event-1",
            "content": "hello world",
            "tags": ["research"],
        }
    )

    assert len(docs) == 1
    doc = docs[0]
    assert doc.source_type == "generic_webhook"
    assert doc.source_hash
    assert doc.doc_id
    assert doc.tags == ["research"]
    assert doc.source_metadata is None


def test_handle_webhook_passes_through_explicit_source_metadata() -> None:
    receiver = WebhookReceiver()

    docs = receiver.handle_webhook(
        {
            "source_type": "web",
            "source_id": "clip-1",
            "source_url": "https://example.com/post",
            "content": "hello world",
            "source_metadata": {
                "kind": "web",
                "domain": "example.com",
                "keywords": ["gar", "metadata"],
            },
        }
    )

    doc = docs[0]
    assert doc.source_metadata is not None
    assert doc.source_metadata.kind == "web"
    extra = doc.source_metadata.model_extra or {}
    assert extra.get("domain") == "example.com"


def test_handle_webhook_keeps_github_metadata_untyped() -> None:
    receiver = WebhookReceiver()

    docs = receiver.handle_webhook(
        {
            "source_type": "github",
            "id": "pr-123",
            "content": "diff summary",
            "repo_name": "voidrot/waygate",
            "branch": "main",
            "commit_sha": "abc123",
            "owner": "voidrot",
            "tech_stack": ["python"],
            "token_count": "99",
        }
    )

    doc = docs[0]
    assert doc.source_type == "github"
    assert doc.source_hash
    # Generic receiver does not own source-specific GitHub metadata models.
    assert doc.source_metadata is None
