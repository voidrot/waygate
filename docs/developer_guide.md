# Developer Guide

This guide helps contributors understand where to look and how to add features.

## Current Contract Baseline (April 2026)

- `RawDocument` and `FrontMatterDocument` carry canonical provenance fields (`doc_id`, `source_url`, `source_hash`, `visibility`, `tags`, `lineage`, `sources`, `source_metadata`).
- `SourceMetadataBase` requires `kind` and allows provider-specific extra fields.
- Storage implementations must preserve canonical frontmatter and support metadata lookup via `get_raw_document_metadata(doc_id)`.
- Compiler publish promotes raw metadata into live frontmatter, including lineage, promoted sources, and aggregated tags.
- GitHub/Slack receiver plugins currently parse webhook payloads into canonical `RawDocument` records.

Out of scope for the current milestone:

- Retrieval-time RBAC filtering engine and broader transport authorization policy.
- Advanced provenance engines beyond current `source_hash` and frontmatter lineage.

- Code layout: packages are under `apps/`, `libs/`, and `plugins/`.
- Adding a new LLM provider: implement `LLMProviderPlugin` in `libs/core` and register the entry point `waygate.plugins.llm`.
- Adding a storage provider: implement `StorageProvider` and register `waygate.plugins.storage`.

Quick pointers to source locations:

- `apps/compiler` — graph building and execution: [graph.py](apps/compiler/src/compiler/graph.py), [worker.py](apps/compiler/src/compiler/worker.py)
- `libs/core` — LLM abstractions and plugin base: [llm_base.py](libs/core/src/waygate_core/llm_base.py), [plugin_base.py](libs/core/src/waygate_core/plugin_base.py)
- `plugins/storage_local` — example local storage provider: [local_storage.py](plugins/storage_local/src/waygate_plugin_local_storage/local_storage.py)

## Testing

- Root test command: `mise run test`
- Fast local run: `mise run test:quick`
- Dependency bootstrap: `mise run uv:sync`

Test placement conventions:

- Prefer package-local tests in `apps/<name>/tests`, `libs/<name>/tests`, and `plugins/<name>/tests`.
- Use root-level `tests/` for cross-workspace tests and shared test utilities.
- Keep unit tests isolated from network and external services by default.

Recent phase test additions:

- Compiler helper/publish behavior tests under `apps/compiler/tests`.
- Schema contract tests for required/extra source metadata behavior under `libs/core/tests`.
- Receiver behavior tests for GitHub and Slack webhook parsing under `plugins/*/tests`.
