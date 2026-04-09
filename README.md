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
- Maintenance now has an explicit sweep command that can detect and persist hash-mismatch, orphan-lineage, and stale-compilation findings as durable maintenance artifacts.
- The maintenance sweep can now optionally enqueue recompilation jobs directly from persisted hash-mismatch or stale-compilation findings, reusing the same compiler queue contract as ingestion.
- The MCP boundary can now persist explicit context-gap reports as durable maintenance artifacts when downstream callers detect missing or insufficient wiki context, and lineage-backed reports can be replayed into the compiler queue.
- The maintenance sweep can now archive orphan-lineage live documents in place, downgrading them to `archived` and prepending a deprecation notice.
- Optional OpenTelemetry tracing can now wrap receiver polling/enqueue, compiler worker/node execution, MCP service calls, and maintenance sweep/remediation flows, while remaining disabled by default for local development.
- Runtime settings can now be sourced either directly from environment variables or, when explicitly enabled, from a Postgres-backed settings table while documents remain in markdown storage.
- The receiver now exposes an admin settings API at `/admin/settings` for core runtime settings and discovered plugin namespaces, with secret values redacted in read responses.

Out of scope (current milestone)

- Transport-level auth, token validation, and end-user RBAC enforcement across retrieval transports.
- Broader provenance engines (for example cryptographic receipts/signatures beyond current hash fields).

Project layout

- Apps: see [apps/](apps/) — `apps/receiver` handles ingestion; `apps/compiler` builds workflow graphs; `apps/mcp_server` exposes the briefing service boundary.
- Apps: see [apps/](apps/) — `apps/operator` hosts the Nuxt operator control plane and Better Auth backend; `apps/receiver` handles ingestion; `apps/compiler` builds workflow graphs; `apps/mcp_server` exposes the briefing service boundary.
- Libraries: see [libs/](libs/) — `libs/core` contains plugin base classes, `libs/storage` defines storage interfaces.
- Plugins: see [plugins/](plugins/) — example providers for Ollama LLMs and local filesystem storage.
- Docs: [docs/overview.md](docs/overview.md) provides a high-level tour; developer guidance is in [docs/developer_guide.md](docs/developer_guide.md).

Quickstart (development)

1. Start any local services defined in `compose.yml` (optional):

```bash
docker compose -f compose.yml up -d
```

This now starts both Valkey and Postgres. Use `POSTGRES_DSN=postgresql://waygate:waygate@localhost:5432/waygate` when enabling database-backed runtime settings.

With `POSTGRES_DSN` configured, the receiver settings API supports:

- `GET /admin/settings` to list the available namespaces.
- `GET /admin/settings/{namespace}` to inspect core or plugin settings with effective source metadata.
- `PATCH /admin/settings/{namespace}` to persist updated values into Postgres.

1. Exercise the receiver with example payloads from `tests.rest` or run individual packages via your workspace tooling.

1. Install the operator frontend workspace dependencies when working on the Nuxt app:

```bash
mise run operator:install
```

1. Run the Nuxt operator app in development:

```bash
pnpm --filter @waygate/operator dev
```

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

1. Run the maintenance sweep and enqueue recompilation jobs for stale or hash-mismatch findings older than 24 hours:

```bash
mise run maintenance:sweep -- --stale-after-hours 24 --enqueue-recompilation
```

1. Replay persisted context-error findings with lineage into the compiler queue:

```bash
mise run maintenance:sweep -- --enqueue-recompilation --include-context-errors
```

1. Archive orphan-lineage live documents in place during the sweep:

```bash
mise run maintenance:sweep -- --archive-orphans
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
- Operator frontend bootstrap: [apps/operator/README.md](apps/operator/README.md)
