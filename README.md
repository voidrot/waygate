# WayGate — Modern LLM Knowledge Base

A combanation of Human usable and agentic Generation-Augmented Retrieval (GAR) Platforms.

---

WayGate is a modular platform for building Generation-Augmented Retrieval (GAR)
workflows inspired by Andrej Karpathy's recent experiments in iterative,
LLM-driven workflow design. The project focuses on ingesting source content,
storing and retrieving documents, and composing LLM-powered generation steps
into repeatable pipelines that refine, validate, and publish knowledge artifacts.

Key goals

- Ingest: accept content from webhooks, polls, or live listeners and normalize it into `RawDocument` objects.
- Store & Retrieve: provide pluggable storage backends for raw and published documents, with simple file/URI semantics.
- Generate: integrate LLM providers via a plugin API to run structured generation and chain outputs into downstream steps.
- Compose: allow graph-based workflows (compiler) that orchestrate generation, review, and publication nodes.

Current implementation snapshot (April 2026)

- Canonical schema fields are implemented on `RawDocument` and `FrontMatterDocument`, including `doc_id`, `source_url`, `source_hash`, `visibility`, `tags`, `lineage`, `sources`, and `source_metadata`.
- Compiled frontmatter now also carries `document_type`, and live filenames are stable human-readable slugs with identity suffixes instead of topic-only names.
- Source-specific metadata contract is enforced via `SourceMetadataBase` with required `kind` and source plugins can attach extra metadata fields.
- Local storage persists canonical raw frontmatter through shared serializers, organizes raw documents by source type, supports live/staging/meta directories, and exposes metadata lookup via `get_raw_document_metadata(doc_id)`.
- Compiler publish promotes provenance from raw metadata into live frontmatter (`lineage`, `sources`, aggregated `tags`).
- Draft generation now consumes reusable markdown template scaffolds from the core library, and receiver state seeds a derived topic instead of the old `Auto-Detect` placeholder.
- First-party GitHub and Slack receivers now parse webhook payloads into canonical `RawDocument` records.
- Retrieval now has an initial internal SDK for loading, filtering, scoring, and token-budgeting live documents from the compiled wiki.
- Maintenance now has an explicit sweep command that can detect and persist hash-mismatch and orphan-lineage findings as durable maintenance artifacts.
- The MCP boundary can now persist explicit context-gap reports as durable maintenance artifacts when downstream callers detect missing or insufficient wiki context.
- Optional OpenTelemetry tracing can now wrap receiver polling/enqueue and compiler worker/node execution, while remaining disabled by default for local development.

Out of scope (current milestone)

- Transport-level auth, token validation, and end-user RBAC enforcement across retrieval transports.
- Broader provenance engines (for example cryptographic receipts/signatures beyond current hash fields).

Project layout

- Apps: see [apps/](apps/) — `apps/receiver` handles ingestion; `apps/compiler` builds workflow graphs; `apps/mcp_server` exposes the briefing service boundary.
- Libraries: see [libs/](libs/) — `libs/core` contains plugin base classes, `libs/storage` defines storage interfaces.
- Plugins: see [plugins/](plugins/) — example providers for Ollama LLMs and local filesystem storage.
- Docs: [docs/overview.md](docs/overview.md) provides a high-level tour; developer guidance is in [docs/developer_guide.md](docs/developer_guide.md).

Quickstart (development)

1. Start any local services defined in `compose.yml` (optional):

```bash
docker compose -f compose.yml up -d
```

1. Exercise the receiver with example payloads from `tests.rest` or run individual packages via your workspace tooling.

Testing

1. Sync workspace dependencies:

```bash
mise run uv:sync
```

1. Run the root test command (pytest + coverage gate):

```bash
mise run test
```

1. For a terse local run:

```bash
mise run test:quick
```

1. Run an explicit maintenance sweep against the current storage backend:

```bash
mise run maintenance:sweep
```

1. Enable optional OpenTelemetry tracing when you want spans emitted from receiver/compiler:

```bash
OTEL_ENABLED=true OTEL_EXPORTER=console mise run test:quick
```

Contributing

- Add LLM providers by implementing `LLMProviderPlugin` in `libs/core` and registering an entry point under `waygate.plugins.llm`.
- Add storage providers by implementing `StorageProvider` and registering under `waygate.plugins.storage`.
- See [docs/developer_guide.md](docs/developer_guide.md) for more details.

Where to look first

- Ingestion and plugin base: [libs/core/src/waygate_core/plugin_base.py](libs/core/src/waygate_core/plugin_base.py)
- Storage interface: [libs/storage/src/waygate_storage/storage_base.py](libs/storage/src/waygate_storage/storage_base.py)
- Compiler entrypoints: [apps/compiler/src/compiler/worker.py](apps/compiler/src/compiler/worker.py)
- Example plugins: [plugins/ollama_provider](plugins/ollama_provider/README.md), [plugins/storage_local](plugins/storage_local/README.md)
