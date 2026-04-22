# waygate-plugin-webhook-generic

WayGate webhook plugin for generic HTTP webhook ingestion. Accepts arbitrary JSON payloads and converts them into `RawDocument` objects for downstream processing. Intended as a starting point and reference implementation for custom webhook integrations.

## Installation

```bash
uv add waygate-plugin-webhook-generic
```

The plugin is discovered automatically via its entry point. No code changes are required.

## Behaviour

- **Payload verification** — passes through without validation by default. Override `verify_webhook_request` in a subclass to add signature checking.
- **Payload enrichment** — returns the payload unchanged by default. Override `enrich_webhook_payload` to add or transform fields before document creation.
- **Payload validation** — validates incoming webhook JSON against a structured payload schema before conversion.
- **Document creation** — maps each payload document to a `RawDocument` and returns the list to the API route for storage and dispatch.

## Payload Contract

The plugin expects JSON with this shape:

```json
{
  "metadata": {
    "event": "document.created",
    "source": "github",
    "topics": ["engineering"],
    "tags": ["release"],
    "originated_at": "2026-04-18T10:30:45.123456Z"
  },
  "documents": [
    {
      "document_type": "markdown",
      "document_name": "release-notes.md",
      "document_path": "docs/release-notes.md",
      "document_hash": "sha256:abc123",
      "content": "# Notes",
      "metadata": {
        "topics": ["docs"],
        "tags": ["public"]
      }
    }
  ]
}
```

Field behavior:

- `metadata.originated_at` is optional. If omitted, the plugin uses the current UTC timestamp.
- `metadata.originated_at` must be ISO-8601 and include a timezone offset.
- `topics` and `tags` from payload metadata and document metadata are merged with stable first-seen ordering and deduplicated.
- `documents[].metadata.topics` and `documents[].metadata.tags` must be arrays of strings when provided.

## Configuration

This plugin has no configuration of its own. Its presence is registered under `WAYGATE_GENERIC_WEBHOOK__*` but no fields are currently defined.

## Security Note

By default, webhook request verification is intentionally permissive for local development and integration testing.

For production use, implement request verification in a subclass by overriding `verify_webhook_request` (for example, HMAC signature checks and replay windows).

## Entry Point

```toml
[project.entry-points."waygate.plugins.webhooks"]
generic_webhook = "waygate_plugin_webhook_generic.plugin:GenericWebhookPlugin"
```

## Extending

Subclass `GenericWebhookPlugin` (or implement `WebhookPlugin` directly from `waygate-core`) to handle a specific webhook provider, adding signature verification and payload normalisation as needed.

## Local Smoke Test

For the minimum local draft pipeline, run the Compose services documented in the
root [README.md](../../README.md), then post the sample payload below.

```bash
curl -X POST http://127.0.0.1:8080/webhooks/generic-webhook \
  -H "Content-Type: application/json" \
  --data @scripts/fixtures/generic-webhook.sample.json
```

Expected behavior:

- The API returns a success payload for the webhook request.
- Raw source artifacts are written to the configured storage backend.
- A `draft.ready` workflow trigger is enqueued through `communication-rq`.
- The draft worker either publishes a compiled markdown document or writes a human-review record.

The sample payload fixture lives at [scripts/fixtures/generic-webhook.sample.json](../../scripts/fixtures/generic-webhook.sample.json).
