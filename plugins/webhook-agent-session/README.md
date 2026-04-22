# waygate-plugin-webhook-agent-session

WayGate webhook plugin for completed agent-session ingestion.

It accepts a structured session payload, verifies authenticity with an optional HMAC signature, stores the normalized session bundle as a raw artifact, and emits `draft.ready` so the existing compile workflow can process the uploaded session transcript.

## Installation

```bash
uv add waygate-plugin-webhook-agent-session
```

The plugin is discovered automatically via its entry point. No application code changes are required.

## Behaviour

- Validates a completed-session payload with a dedicated Pydantic schema.
- Verifies `X-Waygate-Timestamp` and `X-Waygate-Signature` when a signing secret is configured.
- Converts one completed session into one `RawDocument`.
- Stores the canonical transcript and metadata bundle in the raw document body as normalized JSON.
- Emits `draft.ready` with stable session metadata so the compile workflow can consume the transcript through the normal path.

## Configuration

Settings are read from environment variables under `WAYGATE_AGENT_SESSION__*`:

| Variable                                            | Default | Description                                                                                       |
| --------------------------------------------------- | ------- | ------------------------------------------------------------------------------------------------- |
| `WAYGATE_AGENT_SESSION__SIGNING_SECRET`             | none    | Shared secret used to validate HMAC signatures.                                                   |
| `WAYGATE_AGENT_SESSION__ALLOW_UNSIGNED`             | `false` | Permit unsigned requests when no signing secret is configured. Useful for local development only. |
| `WAYGATE_AGENT_SESSION__MAX_TIMESTAMP_SKEW_SECONDS` | `300`   | Maximum allowed absolute skew for the timestamp header.                                           |

When a signing secret is configured, the request must provide:

- `X-Waygate-Timestamp`: Unix epoch seconds
- `X-Waygate-Signature`: `sha256=<hex digest>` of `timestamp + "." + raw_body`

## Payload Contract

The top-level payload must include:

- `schema_version`
- `capture_adapter`
- `capture_adapter_version`
- `provider`
- `surface`
- `exported_at`
- `session`

The `session` object must include:

- `session_id`
- `started_at`
- `completed_at`
- `title`
- `messages`

Each message must include:

- `message_id`
- `turn_index`
- `role`
- `created_at`
- `content`

The plugin also supports optional topics, tags, repository metadata, workspace metadata, tool-call summaries, references, token-usage data, and custom metadata.

## Compile Trigger

This plugin intentionally emits `draft.ready` rather than a custom workflow event. The completed session transcript becomes a raw document, and the current compile workflow remains the downstream consumer.

## Local Smoke Test

The repository includes a fixture payload and helper scripts for a local end-to-end check:

1. Start the mock worker:

```bash
/home/buck/src/voidrot/waygate/.venv/bin/python scripts/mock-worker.py
```

1. Start the web app with the HTTP communication plugin and unsigned local webhook uploads enabled:

```bash
HOST=127.0.0.1 \
PORT=8081 \
WAYGATE_CORE__COMMUNICATION_PLUGIN_NAME=communication-http \
WAYGATE_COMMUNICATION_HTTP__ENDPOINT=http://127.0.0.1:8090/workflows/trigger \
WAYGATE_AGENT_SESSION__ALLOW_UNSIGNED=true \
uv run --all-packages waygate-web
```

1. Post the fixture payload:

```bash
/home/buck/src/voidrot/waygate/.venv/bin/python \
  scripts/post-agent-session.py \
  scripts/fixtures/agent-session.completed.json \
  --endpoint http://127.0.0.1:8081/webhooks/agent-session
```

The web app should return a success payload and the mock worker should log a `draft.ready` trigger whose metadata includes the session id, provider, surface, capture adapter, and schema version.

## Entry Point

```toml
[project.entry-points."waygate.plugins.webhooks"]
agent_session_webhook = "waygate_plugin_webhook_agent_session.plugin:AgentSessionWebhookPlugin"
```
