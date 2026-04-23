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
  "source": "waygate-web.webhooks",
  "document_paths": ["file://raw/01HXYZ-source.txt"],
  "idempotency_key": "optional-string",
  "metadata": {
    "key": "value"
  }
}
```

## Field semantics

- `event_type`: trigger category (for example `draft.ready` or `cron.tick`).
- `event_type`: trigger category (for example `draft.ready`, `ready.integrate`, or `cron.tick`).
- `source`: producer identifier, used for auditability.
- `document_paths`: storage-backed document URIs relevant to the trigger.
- `idempotency_key`: optional deduplication key.
- `metadata`: optional transport-agnostic key/value context.

## Current trigger usage

- `draft.ready` starts the compile workflow from raw artifact URIs.
- `ready.integrate` is emitted after compile writes an approved artifact in the
  `compiled` namespace.
- `ready.integrate` is transport-valid today, but the worker router still treats
  it as a deferred follow-on event and returns `ignored` until the integration
  workflow is implemented.

## HTTP transport

The HTTP communication plugin submits the trigger payload to a worker endpoint.

- Method: `POST`
- Path: `/workflows/trigger`
- Content-Type: `application/json`

### Response body

The shared `waygate-worker-app` HTTP transport accepts the request, schedules the
workflow handoff in the worker process, and returns an acceptance response with a
stable message identifier.

```json
{
  "status": "accepted",
  "message_id": "worker-msg-123"
}
```

## RQ transport

The RQ communication plugin enqueues the trigger payload as a job argument for an
importable Python function.

- Default job function: `waygate_worker.rq.process_rq_workflow_trigger`
- Default draft queue: `draft`
- Default cron queue: `cron`
- Job ID: derived from `idempotency_key` when present and valid for RQ

The plugin returns the RQ job ID as `transport_message_id` when enqueue succeeds.

During the current phased rollout, `ready.integrate` is routed through the same
draft worker path as `draft.ready` so the event can be accepted and explicitly
ignored without introducing a dead-letter backlog.

## NATS transport

The NATS communication plugin publishes the same trigger payload to JetStream.

- Default stream: `WAYGATE_WORKFLOW`
- Default draft subject: `waygate.workflow.draft`
- Default cron subject: `waygate.workflow.cron`
- Publish dedupe header: `Nats-Msg-Id` derived from `event_type` and `idempotency_key` when present

The primary `waygate-worker-app` service consumes those JetStream subjects with explicit
ACKs and periodic `in_progress()` heartbeats so long-running compile jobs do
not redeliver solely because a fixed worker timeout elapsed.

During the current phased rollout, `ready.integrate` is published to the same
draft subject as `draft.ready` so existing workers can accept and ignore it
until the integration workflow is implemented.

## Local HTTP worker

Use the shared worker app for HTTP transport smoke testing:

1. Set `WAYGATE_CORE__COMMUNICATION_PLUGIN_NAME=communication-http`.
1. Start the worker app with `uv run waygate-worker-app`.
1. Ensure producers target `WAYGATE_COMMUNICATION_HTTP__ENDPOINT=http://127.0.0.1:8090/workflows/trigger`.
1. Start the web app or scheduler and trigger a workflow path.
