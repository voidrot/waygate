# Worker Communication Contract

This document defines the worker-facing request contract for communication client plugins.

## Endpoint

- Method: `POST`
- Path: `/workflows/trigger`
- Content-Type: `application/json`

## Request body

```json
{
  "event_type": "draft.ready",
  "source": "waygate-api.webhooks",
  "document_paths": ["raw/abc123.txt"],
  "idempotency_key": "optional-string",
  "metadata": {
    "key": "value"
  }
}
```

## Field semantics

- `event_type`: trigger category (for example `draft.ready` or `cron.tick`).
- `source`: producer identifier, used for auditability.
- `document_paths`: storage paths relevant to the trigger.
- `idempotency_key`: optional deduplication key.
- `metadata`: optional transport-agnostic key/value context.

## Response body

A worker should return an acceptance response with a stable message identifier.

```json
{
  "status": "accepted",
  "message_id": "worker-msg-123"
}
```

## Local mock worker

Use the local mock endpoint for smoke testing:

1. Start mock worker:
   - `uv run python scripts/mock-worker.py`
2. Ensure defaults point to mock worker:
   - `WAYGATE_COMMUNICATION_HTTP__ENDPOINT=http://127.0.0.1:8090/workflows/trigger`
3. Start API or scheduler and trigger a workflow path.
4. Confirm the mock worker logs received payloads and returns `202 Accepted`.
