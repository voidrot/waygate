# Developer Guide

This guide helps contributors understand where to look and how to add features.

## Current Contract Baseline (April 2026)

- `RawDocument` and `FrontMatterDocument` carry canonical provenance fields (`doc_id`, `source_url`, `source_hash`, `visibility`, `tags`, `lineage`, `sources`, `source_metadata`).
- `FrontMatterDocument` also carries `document_type`, which now drives live-document placement under the local GAR filesystem topology.
- `SourceMetadataBase` requires `kind` and allows provider-specific extra fields.
- Storage implementations must preserve canonical frontmatter, support metadata lookup via `get_raw_document_metadata(doc_id)`, and manage the GAR filesystem locations (`raw/`, `live/`, `staging/`, `meta/`).
- Compiler publish promotes raw metadata into live frontmatter, including lineage, promoted sources, aggregated tags, and deterministic live-document naming.
- The compiler draft path now consumes reusable markdown scaffolds from `libs/core/src/waygate_core/file_templates.py` instead of relying solely on inline prompt structure.
- GitHub/Slack receiver plugins currently parse webhook payloads into canonical `RawDocument` records.
- `libs/agent_sdk` provides the live-document retrieval boundary: frontmatter parsing, retrieval-scope visibility filtering, lexical scoring, lineage filtering, and token-budgeted briefing assembly.
- `apps/mcp_server` is a thin transport adapter over the SDK, exposing `generate_briefing` and `preview_retrieval` through FastMCP.
- The compiler package now also exposes an explicit maintenance sweep command that detects and persists maintenance findings through the storage boundary.

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
- `apps/mcp_server` — FastMCP transport surface: [service.py](apps/mcp_server/src/mcp_server/service.py), [server.py](apps/mcp_server/src/mcp_server/server.py), [main.py](apps/mcp_server/src/mcp_server/main.py)
- `libs/agent_sdk` — retrieval repository and policy/scoring seams: [repository.py](libs/agent_sdk/src/waygate_agent_sdk/repository.py), [policy.py](libs/agent_sdk/src/waygate_agent_sdk/policy.py), [scoring.py](libs/agent_sdk/src/waygate_agent_sdk/scoring.py)
- `libs/core` — LLM abstractions and plugin base: [llm_base.py](libs/core/src/waygate_core/llm_base.py), [plugin_base.py](libs/core/src/waygate_core/plugin_base.py)
- `plugins/storage_local` — example local storage provider: [local_storage.py](plugins/storage_local/src/waygate_plugin_local_storage/local_storage.py)

## Testing

- Root test command: `mise run test`
- Fast local run: `mise run test:quick`
- Dependency bootstrap: `mise run uv:sync`
- Maintenance sweep: `mise run maintenance:sweep`

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
