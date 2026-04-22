# Agent Session Webhook Spec

## Status

Historical planning document for the now-implemented feature.

This document records the intended contract before the feature was implemented. It does not redefine current runtime behavior.

## Purpose

Define a first-party WayGate webhook plugin that accepts completed agent-session payloads, stores them durably, and emits `draft.ready` so the existing compile workflow can process the uploaded session transcript.

The design assumes WayGate is the normalized sink, not the capture mechanism. Upstream tools or adapters must decide when a session is complete and then POST the normalized session payload to WayGate.

## Findings

### Upstream boundary

- Current documented GitHub Copilot customization and VS Code chat extensibility expose instructions, MCP, chat participants, tools, participant-scoped history, and feedback hooks.
- Current public docs do not expose a documented generic post-session export hook for arbitrary built-in Copilot Chat sessions.
- Therefore, a WayGate session webhook must assume an explicit upstream adapter. That adapter might be a VS Code extension, a participant-owned export action, a GitHub App, or another service-owned bridge.

### WayGate boundary

- The existing webhook/plugin architecture already supports request verification, payload enrichment, normalization to `RawDocument`, and automatic route registration.
- The API ingress path is currently hard-coded to emit `draft.ready` via `send_draft_message()` after writing raw artifacts.
- `RawDocument` has richer in-memory metadata than the stored raw artifact currently preserves.
- The current raw artifact frontmatter and workflow parser do not preserve a full conversation or transcript model.

## Scope

### Included

- Completed-session uploads only.
- A dedicated webhook plugin package at `plugins/webhook-agent-session`.
- A backward-compatible API dispatch generalization so dedicated webhook plugins can attach stable metadata and idempotency while still using `draft.ready`.
- Reference scripts and fixtures for building and posting signed session payloads.

### Excluded

- Incremental per-turn streaming in the first iteration.
- Passive interception of arbitrary built-in Copilot Chat sessions.
- A worker-side session-processing workflow unless explicitly added later.

## Recommended Architecture

### 1. New webhook plugin

Create a first-party plugin package:

- `plugins/webhook-agent-session/pyproject.toml`
- `plugins/webhook-agent-session/src/waygate_plugin_webhook_agent_session/__init__.py`
- `plugins/webhook-agent-session/src/waygate_plugin_webhook_agent_session/models.py`
- `plugins/webhook-agent-session/src/waygate_plugin_webhook_agent_session/plugin.py`
- `plugins/webhook-agent-session/tests/`
- `plugins/webhook-agent-session/README.md`

The plugin should:

- expose a stable plugin name such as `agent-session`
- validate a completed-session payload with Pydantic
- verify request authenticity
- normalize one completed session into one stored raw artifact
- emit `draft.ready` intentionally so the current compile workflow stays the downstream consumer

### 2. Backward-compatible dispatch seam

The API should stop assuming every webhook maps to the exact same fixed trigger object.

Recommended implementation:

- keep `send_draft_message()` as a compatibility helper
- add a generic submit helper that accepts a full `WorkflowTriggerMessage`
- extend `WebhookPlugin` with a default `build_workflow_trigger()` method
- keep the default behavior identical for existing webhook plugins
- let the new session plugin emit `draft.ready` while attaching a stable session idempotency key and session metadata

### 3. Durable session representation

The canonical session bundle should live in the raw artifact body, not only in frontmatter.

Recommended first iteration:

- compute a canonical normalized JSON bundle from the validated payload
- use that canonical bundle to derive a stable `source_hash`
- store a pretty-printed JSON form of the same bundle in `RawDocument.content`
- use top-level `RawDocument` fields only for durable routing and indexing fields such as `source_id`, `timestamp`, `topics`, and `tags`

This avoids losing important transcript metadata across the current raw artifact boundary.

## Route

The new route should be registered automatically as:

- `POST /webhooks/agent-session`

## Payload Contract

### Top-level fields

Required fields:

- `schema_version`
- `capture_adapter`
- `capture_adapter_version`
- `provider`
- `surface`
- `exported_at`
- `session`

Optional fields:

- `visibility`
- `privacy_mode`
- `redaction_summary`
- `organization`
- `installation_id`
- `custom_metadata`

### Session fields

Required fields:

- `session_id`
- `started_at`
- `completed_at`
- `title`
- `messages`

Optional fields:

- `thread_id`
- `subthread_id`
- `conversation_url`
- `summary`
- `topics`
- `tags`
- `workspace`
- `repository`
- `token_usage`
- `attachments`
- `references`
- `custom_metadata`

### Message fields

Required fields:

- `message_id`
- `turn_index`
- `role`
- `created_at`
- `content`

Optional fields:

- `model`
- `participant`
- `command`
- `tool_calls`
- `tool_results`
- `references`
- `citations`
- `token_usage`
- `error`
- `custom_metadata`

## Security Contract

Recommended first iteration:

- sign requests with `X-Waygate-Timestamp` and `X-Waygate-Signature`
- compute HMAC-SHA256 over `timestamp + "." + raw_body`
- reject stale timestamps outside a small replay window
- allow an explicit unsigned development mode only by configuration

## Idempotency

Preferred derivation order:

1. adapter-provided `session_id`
2. provider and session identifier tuple
3. SHA-256 of the canonical normalized payload

The dedicated plugin should attach a stable session-level idempotency key to the `draft.ready` trigger.

## Scripts

Recommended repo-local scripts:

1. `scripts/build-agent-session-payload.py`
2. `scripts/post-agent-session.py`
3. `scripts/fixtures/agent-session.completed.json`

## Implementation Plan

1. Add this planning spec.
2. Generalize the legacy webhook dispatch seam while preserving `draft.ready` as the default compile trigger.
3. Extend the webhook plugin contract with a default trigger builder.
4. Create the `agent-session` webhook plugin package.
5. Add fixture and helper scripts.
6. Add unit and API tests.
7. After the feature is implemented, update the current design docs to reflect the new runtime contract.

## Verification Plan

1. Unit-test payload validation, signature verification, idempotency derivation, and content normalization.
2. Extend API client tests to cover generic workflow submission.
3. Confirm existing generic webhook behavior still emits `draft.ready`.
4. Add a route or OpenAPI-level assertion proving the new session webhook is registered.
5. Run a smoke test against the API using the helper script and fixture payload.
