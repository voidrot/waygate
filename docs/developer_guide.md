# Developer Guide

This guide helps contributors understand where to look and how to add features.

## Current Contract Baseline (April 2026)

- `RawDocument` and `FrontMatterDocument` carry canonical provenance fields (`doc_id`, `source_url`, `source_hash`, `visibility`, `tags`, `lineage`, `sources`, `source_metadata`).
- `FrontMatterDocument` also carries `document_type`, which now drives live-document placement under the local GAR filesystem topology.
- `SourceMetadataBase` requires `kind` and allows provider-specific extra fields.
- Storage implementations must preserve canonical frontmatter, support metadata lookup via `get_raw_document_metadata(doc_id)` and raw URI lookup via `get_raw_document_uri(doc_id)`, and manage the GAR filesystem locations (`raw/`, `live/`, `staging/`, `meta/`).
- Compiler publish promotes raw metadata into live frontmatter, including lineage, promoted sources, aggregated tags, and deterministic live-document naming.
- The compiler draft path now consumes reusable markdown scaffolds from `libs/core/src/waygate_core/file_templates.py` instead of relying solely on inline prompt structure.
- GitHub/Slack receiver plugins currently parse webhook payloads into canonical `RawDocument` records.
- `libs/agent_sdk` provides the live-document retrieval boundary: frontmatter parsing, retrieval-scope visibility filtering, lexical scoring, lineage filtering, and token-budgeted briefing assembly.
- `apps/mcp_server` is a thin transport adapter over the SDK, exposing `generate_briefing` and `preview_retrieval` through FastMCP.
- `apps/mcp_server` also exposes `report_context_error`, which persists an explicit context-gap report as a maintenance artifact through the shared storage contract and emits a lineage-backed recompilation signal when replay is possible.
- The MCP boundary treats request-supplied scope fields as advisory: effective visibilities are clamped to the server-side allowlist, and a configured default role overrides the request role.
- The compiler package now also exposes an explicit maintenance sweep command that detects and persists maintenance findings through the storage boundary, including optional chrono-decay detection for stale live documents.
- Storage implementations must also support in-place live document updates via `update_live_document(uri, content)` so maintenance remediation can archive affected docs without changing their URI.
- `libs/core/src/waygate_core/observability.py` now provides optional OpenTelemetry setup and span helpers for receiver/compiler/MCP seams, including maintenance sweep/remediation flows; tracing is disabled unless `OTEL_ENABLED=true`.

Out of scope for the current milestone:

- External IAM, scoped tokens, and end-user RBAC beyond the caller-supplied retrieval scope.
- Vector search, BM25 indexes, and LLM re-ranking implementations beyond the current lexical scorer seams.
- Advanced provenance engines beyond current `source_hash` and frontmatter lineage.

- Code layout: packages are under `apps/`, `libs/`, and `plugins/`.
- Adding a new LLM provider: implement `LLMProviderPlugin` in `libs/core` and register the entry point `waygate.plugins.llm`.
- Adding a storage provider: implement `StorageProvider` and register `waygate.plugins.storage`.

Quick pointers to source locations:

- `apps/compiler` — graph building and execution: [graph.py](apps/compiler/src/compiler/graph.py), [worker.py](apps/compiler/src/compiler/worker.py)
- `apps/compiler` maintenance sweep entrypoint: [maintenance.py](apps/compiler/src/compiler/maintenance.py)
- `apps/compiler` observability seam: [middleware.py](apps/compiler/src/compiler/middleware.py)
- `apps/receiver` observability seams: [app.py](apps/receiver/src/receiver/app.py), [scheduler.py](apps/receiver/src/receiver/core/scheduler.py), [trigger.py](apps/receiver/src/receiver/services/trigger.py)
- `apps/mcp_server` — FastMCP transport surface: [service.py](apps/mcp_server/src/mcp_server/service.py), [server.py](apps/mcp_server/src/mcp_server/server.py), [main.py](apps/mcp_server/src/mcp_server/main.py)
- `libs/agent_sdk` — retrieval repository and policy/scoring seams: [repository.py](libs/agent_sdk/src/waygate_agent_sdk/repository.py), [policy.py](libs/agent_sdk/src/waygate_agent_sdk/policy.py), [scoring.py](libs/agent_sdk/src/waygate_agent_sdk/scoring.py)
- `libs/core` — LLM abstractions and plugin base: [llm_base.py](libs/core/src/waygate_core/llm_base.py), [plugin_base.py](libs/core/src/waygate_core/plugin_base.py)
- `plugins/storage_local` — example local storage provider: [local_storage.py](plugins/storage_local/src/waygate_plugin_local_storage/local_storage.py)

## Testing

- Root test command: `mise run test`
- Fast local run: `mise run test:quick`
- Dependency bootstrap: `mise run uv:sync`
- Maintenance sweep: `mise run maintenance:sweep`
- Maintenance sweep with queued recompilation handoff: `mise run maintenance:sweep -- --enqueue-recompilation`
- Maintenance sweep with stale-doc detection: `mise run maintenance:sweep -- --stale-after-hours 24 --enqueue-recompilation`
- Maintenance sweep replaying persisted context errors: `mise run maintenance:sweep -- --enqueue-recompilation --include-context-errors`
- Maintenance sweep archiving orphan docs: `mise run maintenance:sweep -- --archive-orphans`

Observability env surface:

- `OTEL_ENABLED` default `false`
- `OTEL_EXPORTER` supported values: `console`, `otlp`
- `OTEL_SERVICE_NAMESPACE` default `waygate`

Test placement conventions:

- Prefer package-local tests in `apps/<name>/tests`, `libs/<name>/tests`, and `plugins/<name>/tests`.
- Use root-level `tests/` for cross-workspace tests and shared test utilities.
- Keep unit tests isolated from network and external services by default.

Recent phase test additions:

- Compiler helper/publish behavior tests under `apps/compiler/tests`.
- Schema contract tests for required/extra source metadata behavior under `libs/core/tests`.
- Receiver behavior tests for GitHub and Slack webhook parsing under `plugins/*/tests`.
- Retrieval SDK ranking/visibility tests under `libs/agent_sdk/tests`.
- MCP service and transport tests under `apps/mcp_server/tests`.
