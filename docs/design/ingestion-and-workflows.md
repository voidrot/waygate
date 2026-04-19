# Ingestion and Workflow Pipeline

## Purpose

This document describes how raw content enters the system, how work is dispatched, and how the current compile workflow turns stored raw documents into published markdown.

## Producer Flows

WayGate currently has two producer paths:

- webhook-driven ingestion in `apps/api`
- schedule-driven triggers in `apps/scheduler`

Both paths converge on the same `WorkflowTriggerMessage` contract.

## Webhook Ingestion Flow

The API mounts one route per discovered webhook plugin under `/webhooks/<plugin-name>`.

For each request, the route handler does the following:

1. read the raw request body and headers
2. call `verify_webhook_request()` on the plugin
3. parse and optionally enrich the JSON payload
4. call `handle_webhook()` to obtain `RawDocument` objects
5. render each raw document and write it into the `raw` namespace
6. send a `draft.ready` workflow trigger containing the written document URIs

Raw documents are stored under generated UUIDv7-based filenames with a `.txt` suffix.

## Scheduler Flow

The scheduler bootstraps the shared app context, resolves the configured communication client, and registers one APScheduler job per installed cron plugin.

For each scheduled run, it:

1. calls `cron_plugin.run()` with minimal execution context
2. sends a `cron.tick` workflow trigger
3. includes the cron expression in trigger metadata

The scheduler and API therefore share the same dispatch surface even though they produce different trigger categories.

## Workflow Trigger Contract

The transport-neutral message shape is `WorkflowTriggerMessage`.

| Field             | Meaning                                               |
| ----------------- | ----------------------------------------------------- |
| `event_type`      | Trigger category such as `draft.ready` or `cron.tick` |
| `source`          | Producer identity for auditability                    |
| `document_paths`  | Storage-backed document URIs relevant to the trigger  |
| `idempotency_key` | Optional deduplication key                            |
| `metadata`        | Optional string-to-string transport-neutral context   |

Current example payload:

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

Current transport adapters:

- HTTP: POST JSON to `/workflows/trigger`
- RQ: enqueue the payload for `waygate_workflows.draft.jobs.process_workflow_trigger`

The important design point is that producers depend on the message contract, not the transport.

## Transport Behavior

### HTTP communication plugin

The HTTP plugin is a transport client, not a workflow implementation by itself.

Current behavior:

- submits JSON to the configured endpoint
- defaults to `http://localhost:8090/workflows/trigger`
- can attach an auth token header when configured
- retries transient connection and eligible HTTP failures with exponential backoff
- returns the worker response `message_id` as `transport_message_id` when present
- rejects `draft.ready` messages that do not include at least one document path

Current worker-side status in this repo:

- the repository includes a local mock HTTP worker in `scripts/mock-worker.py`
- that mock endpoint accepts `POST /workflows/trigger` and returns `202 Accepted`
- the repo does not currently ship a first-party HTTP worker service that executes the compile workflow end to end

Expected acceptance response shape:

```json
{
  "status": "accepted",
  "message_id": "worker-msg-123"
}
```

### RQ communication plugin

The RQ plugin is the concrete workflow execution transport currently implemented in the repo.

Current behavior:

- `draft.ready` routes to the configured draft queue
- `cron.tick` routes to the configured cron queue
- the default job function is `waygate_workflows.draft.jobs.process_workflow_trigger`
- when `idempotency_key` is present, the plugin sanitizes it and builds a job id as `<event_type>-<sanitized-key>`
- duplicate jobs are treated as accepted and return the existing job id as `transport_message_id`
- Redis resolution falls back from plugin config to core Redis settings, then to `redis://localhost:6379/0`

This is the transport that currently connects producer-side trigger dispatch to the implemented workflow router.

## Worker-Side Trigger Handling

`waygate_workflows.router.process_workflow_trigger()` is the current worker-side entrypoint behind the default RQ job function.

Current behavior:

- validates the payload as `WorkflowTriggerMessage`
- builds a stable workflow request key as `compile:<idempotency_key>` when present, otherwise from a hash of sorted document paths
- invokes the LangGraph compile workflow for `draft.ready`
- returns a structured result for completed publishes or human-review interrupts
- returns `ignored` for unsupported event types

Current result shapes:

### Completed draft workflow

```json
{
  "status": "completed",
  "request_key": "compile:draft-123",
  "document_paths": ["file://raw/source.txt"],
  "metadata": {
    "origin": "unit-test"
  },
  "source_set_key": "hash-abc",
  "published_document_uri": "file://published/hash-abc.md",
  "published_document_id": "hash-abc"
}
```

### Human review interrupt

```json
{
  "status": "human_review",
  "request_key": "compile:draft-789",
  "document_paths": ["file://raw/source.txt"],
  "metadata": {},
  "source_set_key": "hash-review",
  "human_review_record_uri": "file://review/hash-review.json",
  "interrupts": [
    {
      "value": {
        "type": "compile_human_review"
      }
    }
  ]
}
```

### Unsupported event type

```json
{
  "status": "ignored",
  "event_type": "unknown.event",
  "document_paths": [],
  "metadata": {}
}
```

## Draft Versus Cron Trigger Status

The producer-side contract and communication plugins recognize both `draft.ready` and `cron.tick`.

The current worker-side implementation does not handle both equally:

- `draft.ready` is implemented end to end
- `cron.tick` is dispatched and queued, but the default workflow router does not execute a cron workflow for it yet

That means `cron.tick` is currently part of the transport contract and scheduler integration boundary, but not part of the completed workflow execution surface in `libs/workflows`.

## Compile Workflow: Implemented Behavior

The compile workflow in `libs/workflows` is a real LangGraph workflow, not only a design sketch.

Its current node sequence is:

1. `normalize_request`
2. `compile_source_document` fan-out
3. `synthesis`
4. `review`
5. `publish` or `human_review`

## Phase Details

### 1. Normalize request

`normalize_request` reads each raw document from storage and parses it into a `SourceDocumentState` with:

- `uri`
- `content`
- `source_hash`
- `source_uri`
- `source_type`
- `timestamp`

It also derives a stable `source_set_key`.

The current workflow requires one of these complete coverage modes for the entire source set:

- every source document has `source_hash`, producing `hash-<sha256>`
- every source document has `source_uri`, producing `uri-<sha256>`

Mixed or incomplete coverage is rejected.

### 2. Per-source compile fan-out

`fan_out_source_documents()` sends one active source document at a time to `compile_source_document`.

Each compile worker performs two LLM-backed tasks:

- grounded metadata extraction into tags, topics, people, organizations, and projects
- concise summary extraction with key claims and defined terms

The workflow state merges those results using reducers:

- metadata and summaries append across documents
- the scratchpad deduplicates discovered terms and claims

### 3. Synthesis

`synthesize_draft()` combines document summaries, extracted metadata, and the scratchpad into a single Markdown draft. The output becomes `current_draft` and moves the workflow into review status.

### 4. Review

`review_draft()` uses the configured review model to check the draft against the parsed source documents.

The current review loop is simple and explicit:

- approved drafts go straight to publish
- rejected drafts return to synthesis
- after `MAX_REVISIONS = 3`, the workflow escalates to human review

This is the actual baseline that any future structured-consensus work must extend.

### 5. Human review

`human_review_gate()` writes a JSON record to the `review` namespace and pauses execution with a LangGraph interrupt.

The stored review record includes:

- `source_set_key`
- raw document URIs
- accumulated review feedback
- current draft
- allowed resume actions
- revision count

Resume decisions are limited to:

- `resume_to_synthesis`
- `resume_to_publish`

### 6. Publish

`publish_draft()` writes the final markdown artifact to the `published` namespace as:

- `published/<source_set_key>.md`

The body is the current Markdown draft. Frontmatter is added by `render_published_document()` and currently includes:

- `doc_id`
- `source_set_key`
- `source_documents`
- `source_hashes`
- `source_uris`
- `compiled_at`
- `review_feedback`
- aggregated `tags`, `topics`, `people`, `organizations`, and `projects`

## Historical Spec Versus Current Code

`docs/plans/compile-workflow-original-plan.md` preserves the original target architecture, but it is broader than the code that exists today.

The current implementation does include:

- map-style per-source processing
- shared scratchpad/state reduction
- bounded review retries
- human-review escalation
- storage-backed publish output
- a concrete worker-side router returning `completed`, `human_review`, or `ignored`
- a concrete transport contract implemented by communication plugins

The current implementation does not include:

- vector database or PostgreSQL publish side effects
- a separate compiler app package
- downstream static-site rebuilds
- multi-review or multi-draft consensus
- a first-party HTTP worker service beyond the mock worker
- cron workflow execution behind the default worker router

Those items remain future work. The implemented baseline in this repo is the storage-backed compile, review, human-review, and publish path described above.

When updating workflow code or docs, treat the code in `libs/workflows` as the source of truth for current behavior.

## Planned Compile Evolution

The target compile architecture is planned to move away from the current per-document fan-out.

The intended replacement is a supervisor-centered multi-agent design inside a LangGraph workflow. In that target model:

1. document analysis runs in a stable order rather than a broad parallel fan-out
2. each document-analysis pass receives bounded prompt context derived from durable workflow state plus the active document
3. accumulated discoveries such as canonical topics, tags, glossary terms, entities, and claims are carried forward between passes
4. synthesis, review, human-review interrupt, and publish remain explicit workflow boundaries

This change is motivated by consistency rather than throughput. Later document passes should be able to reuse prior discoveries and resolve cross-document references instead of rediscovering shared concepts from scratch.

### Current-to-target mapping

| Current responsibility    | Planned target responsibility                                   |
| ------------------------- | --------------------------------------------------------------- |
| `normalize_request`       | normalize request and build stable document order               |
| `compile_source_document` | source analysis specialist under supervisor control             |
| `synthesis`               | synthesis specialist after sequential source analysis completes |
| `review`                  | review specialist with the same bounded retry policy            |
| `human_review`            | human-review specialist and interrupt boundary                  |
| `publish`                 | deterministic publish boundary                                  |

### Contracts that must stay stable during migration

Even if the compile internals evolve, these contracts should remain stable:

- `WorkflowTriggerMessage` input shape
- thread id derivation in the worker router
- `source_set_key` derivation semantics
- review retry and human-review escalation semantics
- human-review resume payload shape
- completed, human-review, and ignored result shapes returned by the router
- published markdown and frontmatter as durable outputs

### Planned future state model

The future compile state should be split into:

- durable workflow state, which is checkpointed and resumed
- transient per-pass prompt context, which is reconstructed for each document-analysis call and discarded afterward

The proposed typed schema for that future state lives in [docs/plans/compile-multi-agent-supervisor-migration-plan.md](../plans/compile-multi-agent-supervisor-migration-plan.md). It is planning guidance only and is not the current implementation contract.
