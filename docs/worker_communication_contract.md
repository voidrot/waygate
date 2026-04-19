# Worker Communication Contract

This document defines the producer-side workflow trigger payload used by
communication client plugins. The payload is transport-agnostic: HTTP-based
workers and RQ-based workers both consume the same `WorkflowTriggerMessage`
shape.

## Trigger payload

## Request body

```json
{
  "event_type": "draft.ready",
  "source": "waygate-api.webhooks",
  "document_paths": ["file://raw/01HXYZ-source.txt"],
  "idempotency_key": "optional-string",
  "metadata": {
    "key": "value"
  }
}
```

## Field semantics

- `event_type`: trigger category (for example `draft.ready` or `cron.tick`).
- `source`: producer identifier, used for auditability.
- `document_paths`: storage-backed document URIs relevant to the trigger.
- `idempotency_key`: optional deduplication key.
- `metadata`: optional transport-agnostic key/value context.

## HTTP transport

The HTTP communication plugin submits the trigger payload to a worker endpoint.

- Method: `POST`
- Path: `/workflows/trigger`
- Content-Type: `application/json`

### Response body

An HTTP worker should return an acceptance response with a stable message identifier.

```json
{
  "status": "accepted",
  "message_id": "worker-msg-123"
}
```

## RQ transport

The RQ communication plugin enqueues the trigger payload as a job argument for an
importable Python function.

- Default job function: `waygate_workflows.draft.jobs.process_workflow_trigger`
- Default draft queue: `draft`
- Default cron queue: `cron`
- Job ID: derived from `idempotency_key` when present and valid for RQ

The plugin returns the RQ job ID as `transport_message_id` when enqueue succeeds.

## Local mock worker

Use the local mock endpoint for smoke testing:

1. Start mock worker:
   - `uv run python scripts/mock-worker.py`
2. Ensure defaults point to mock worker:
   - `WAYGATE_COMMUNICATION_HTTP__ENDPOINT=http://127.0.0.1:8090/workflows/trigger`
3. Start API or scheduler and trigger a workflow path.
4. Confirm the mock worker logs received payloads and returns `202 Accepted`.
