# WayGate Architecture

## Purpose

WayGate is a Python monorepo for building Generation-Augmented Retrieval workflows around a shared plugin runtime. In the current repository, the center of gravity is not a single monolith. It is a set of small apps that all boot the same core runtime, exchange the same workflow trigger contract, and persist their durable artifacts through storage plugins.

## Current System Shape

The repository is organized into three layers.

- `apps`: `web`, `scheduler`, `draft-worker`, `nats-worker`
  Responsibility: long-running processes that expose the operator UI, HTTP ingress, schedule recurring jobs, or execute workflow work over RQ or JetStream.
- `libs`: `core`, `webhooks`, `worker`, `workflows`
  Responsibility: shared runtime primitives, worker execution helpers, plugin contracts, configuration, and workflow implementation.
- `plugins`: `local-storage`, `provider-ollama`, `provider-featherless-ai`, `communication-http`, `communication-nats`, `communication-rq`, `webhook-generic`, `webhook-agent-session`
  Responsibility: first-party implementations of the plugin interfaces defined in `waygate-core`.

## Package Boundaries

### apps/web

- Unified FastAPI host for the server-rendered operator UI.
- Initializes AuthTuna for browser and API-oriented auth flows.
- Mounts the reusable webhook ingress app from `libs/webhooks` under `/webhooks`.
- Merges mounted webhook OpenAPI endpoints into the parent docs so the web app is the primary API surface.

### libs/webhooks

- Owns the mountable FastAPI webhook ingress sub-application.
- Discovers webhook plugins and registers one route per plugin.
- Persists normalized raw documents through the configured storage plugin.
- Asks the matched webhook plugin to build the downstream workflow trigger after storage writes complete.
- Dispatches that workflow trigger through the configured communication plugin. The default webhook behavior still emits `draft.ready`.
- Owns webhook-specific OpenAPI helpers so mounted routes can still appear in the parent app's docs.

### apps/scheduler

- Bootstraps the same app context as the web app.
- Loads installed cron plugins and schedules them with APScheduler.
- Dispatches `cron.tick` messages through the same communication client contract used by the web app.

### apps/draft-worker

- RQ worker runtime for queued workflow execution.
- Depends on `waygate-workflows` for importable job entrypoints.
- Consumes the RQ communication plugin configuration and listens on the configured draft queue.
- Preflights the active compile-workflow LLM provider before polling Redis so provider-construction errors fail at startup.
- The concrete worker-side workflow entrypoint currently resolves to `waygate_workflows.draft.jobs.process_workflow_trigger`.

### apps/nats-worker

- JetStream worker runtime for durable workflow execution.
- Consumes the `draft.ready` and `cron.tick` subjects configured by `communication-nats`.
- Uses the shared helpers in `libs/worker` to extend ACK leases while long-running workflow steps execute.
- Preflights the active compile-workflow LLM provider before polling JetStream so provider-construction errors fail at startup.

### libs/core

- Defines the WayGate bootstrap path.
- Owns plugin hooks, abstract base classes, config merging, logging setup, and common schema types.
- Produces the frozen `WaygateAppContext` shared by all runtime processes.

### libs/worker

- Holds worker-runtime helpers shared across transport-specific worker apps.
- Currently ships the JetStream consumer loop used by `apps/nats-worker`.
- Keeps workflow execution concerns separate from transport configuration and settlement mechanics.

### libs/workflows

- Implements the compile workflow using LangGraph.
- Keeps workflow logic importable and independent from any single worker transport.
- Defines workflow state, node behavior, and publish/human-review boundaries.

## Core Design Choices

### Plugin-first runtime

Core does not hardcode concrete storage, webhook, LLM, cron, or communication implementations. Apps always resolve those capabilities through the shared plugin manager and the merged app context.

### Shared bootstrap path

Every process starts from the same sequence:

1. configure logging
2. load installed plugins
3. discover plugin config schemas
4. build merged settings
5. instantiate grouped plugins

This keeps app startup predictable and prevents each process from inventing its own plugin wiring rules.

### Storage-backed durability

The durable artifacts in the current repository are storage-backed files:

- raw source documents
- human-review records
- published compiled markdown
- metadata/templates/agents content for storage plugins that provide those namespaces

The repository may also persist relational secondary indexes in Postgres for document metadata, workflow jobs, job transitions, document/job edit history, and vector references. Those tables are reconstructable operational indexes and do not replace the storage-backed artifacts as the source of truth.

The current implementation does not treat a search index, vector store, static site, or UI layer as a source of truth.

### Transport-agnostic workflow dispatch

The web app and scheduler do not know whether work is being delivered over HTTP, JetStream, or RQ. They both send a `WorkflowTriggerMessage` and rely on communication plugins to handle the transport-specific details.

### Workflow logic separate from worker runtime

Compile behavior lives in `libs/workflows`, not in the web app or the worker process itself. This makes the workflow reusable across transports and easier to test in isolation.

## Planned Workflow Evolution

The current compile implementation is a single LangGraph workflow with per-document fan-out followed by synthesis and review.

The planned target architecture keeps LangGraph as the durable orchestration layer but moves compile control toward a supervisor-centered multi-agent model.

That planned evolution has three important constraints:

1. the supervisor pattern is preferred over a router because compile needs ongoing, stateful orchestration rather than one-shot classification
2. handoffs are not the primary compile mechanism; they remain a better fit for human-review or operator-controlled transitions
3. multiple raw documents should be analyzed in a stable sequence rather than a large parallel fan-out so each later pass can inherit prior discoveries

The planned target design is documented in [docs/design/compile-supervisor-multi-agent.md](./compile-supervisor-multi-agent.md).

## End-to-End Flow

The current repo supports this main path:

1. A webhook request reaches the mounted webhook surface in `apps/web`.
2. The selected webhook plugin verifies, enriches, and converts the payload into `RawDocument` objects.
3. The webhook ingress app writes those raw documents into storage.
4. The ingress app asks the webhook plugin to build the downstream workflow trigger for the written document URIs.
5. In the default case, that trigger is still `draft.ready`; dedicated webhook plugins can attach metadata, stable idempotency keys, or skip dispatch entirely.
6. A worker consumes the trigger and runs the compile workflow from `libs/workflows`.
7. The workflow writes a published markdown document or, on repeated review failure, a human-review record.

The scheduler uses the same dispatch path, but it starts from cron plugins and emits `cron.tick` instead of `draft.ready`.

Today that shared producer contract is broader than the implemented worker router: `libs/workflows` currently processes `draft.ready` and ignores unsupported event types, so `cron.tick` is a defined trigger shape and dispatch path, not yet a completed workflow execution path in the current repo.

## Current Boundaries

Implemented in this repo today:

- plugin loading and merged configuration
- webhook ingestion through FastAPI
- transport-agnostic workflow trigger dispatch
- JetStream worker support for durable workflow execution
- RQ worker support for queued draft work
- LangGraph compile, review, publish, and human-review interruption flow
- storage-backed raw, review, and published document artifacts
- HTTP transport as a communication client contract plus a local mock worker for smoke testing

Not implemented in this repo today:

- a dedicated browser client separate from the server-rendered FastAPI web app
- a retrieval SDK or MCP server package
- hybrid lexical/vector retrieval infrastructure
- graph traversal over published content
- static-site publishing pipeline
- publish-triggered deployment hooks
- cryptographic provenance receipts
- a first-party HTTP worker service that executes the workflow contract end to end
- worker-side handling for `cron.tick`

## Legacy Mapping

Several legacy docs described the right long-term direction, but with names that no longer match the current repository. The main mappings are:

| Legacy term  | Current repo term                                        |
| ------------ | -------------------------------------------------------- |
| receiver     | `apps/web` mounted with `libs/webhooks`                  |
| compiler app | `libs/workflows` plus RQ and JetStream worker processes. |
| live wiki    | `published` storage namespace                            |
| meta         | `metadata`, `templates`, and `agents` storage namespaces |

Use the current names when writing new documentation or code.

In the current repository, "worker apps" means `apps/draft-worker` for the legacy RQ path or `apps/nats-worker` for the JetStream-backed path.
