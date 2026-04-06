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

Project layout

- Apps: see [apps/](apps/) — `apps/receiver` handles ingestion; `apps/compiler` builds and runs workflow graphs.
- Libraries: see [libs/](libs/) — `libs/core` contains plugin base classes, `libs/storage` defines storage interfaces.
- Plugins: see [plugins/](plugins/) — example providers for Ollama LLMs and local filesystem storage.
- Docs: [docs/overview.md](docs/overview.md) provides a high-level tour; developer guidance is in [docs/developer_guide.md](docs/developer_guide.md).

Quickstart (development)

1. Start any local services defined in `compose.yml` (optional):

```bash
docker compose -f compose.yml up -d
```

1. Exercise the receiver with example payloads from `tests.rest` or run individual packages via your workspace tooling.

Contributing

- Add LLM providers by implementing `LLMProviderPlugin` in `libs/core` and registering an entry point under `waygate.plugins.llm`.
- Add storage providers by implementing `StorageProvider` and registering under `waygate.plugins.storage`.
- See [docs/developer_guide.md](docs/developer_guide.md) for more details.

Where to look first

- Ingestion and plugin base: [libs/core/src/waygate_core/plugin_base.py](libs/core/src/waygate_core/plugin_base.py)
- Storage interface: [libs/storage/src/waygate_storage/storage_base.py](libs/storage/src/waygate_storage/storage_base.py)
- Compiler entrypoints: [apps/compiler/src/compiler/worker.py](apps/compiler/src/compiler/worker.py)
- Example plugins: [plugins/ollama_provider](plugins/ollama_provider/README.md), [plugins/storage_local](plugins/storage_local/README.md)
