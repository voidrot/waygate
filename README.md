# WayGate

WayGate is a modular platform for building **Generation-Augmented Retrieval (GAR)** workflows. It provides a plugin-based runtime for ingesting content via webhooks, storing and managing documents, driving LLM generation pipelines, and scheduling recurring jobs — all wired together through a shared configuration and plugin registry.

## Monorepo Structure

```
apps/
  api/          — FastAPI HTTP server; exposes webhook endpoints and the OpenAPI schema
  scheduler/    — Background job runner for cron-style workflows
libs/
  core/         — Shared framework: plugin system, config registry, bootstrap, logging
plugins/
  local-storage/    — StoragePlugin backed by the local filesystem
  provider-ollama/  — LLMProviderPlugin backed by a local Ollama server
  webhook-generic/  — WebhookPlugin for generic HTTP webhook ingestion
```

## How It Works

1. **Bootstrap** — call `bootstrap_app()` from `waygate-core`. It loads all installed plugins via setuptools entry points, discovers their config schemas, builds a merged Pydantic settings object (populated from environment variables), and instantiates each plugin with its config injected.

2. **Configuration** — all settings live under the `WAYGATE_` env prefix. Core settings use `WAYGATE_CORE__*`; each plugin gets its own namespace derived from its plugin name (e.g. `WAYGATE_LOCAL_STORAGE__BASE_PATH`).

3. **Plugins** — plugins implement one or more pluggy hook specs defined in `waygate-core`. Installing a plugin package and declaring its entry point is sufficient; no code changes to the core are needed.

## Quick Start

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/).

```bash
# Install all packages
uv sync --all-packages

# Run the API server
uv run waygate-api

# Run the scheduler
uv run waygate-scheduler
```

Copy `env.example` to `.env` and set values appropriate for your environment before starting.

## Packages

| Package | Description |
|---|---|
| [`waygate-core`](libs/core/) | Plugin system, config registry, bootstrap |
| [`waygate-api`](apps/api/) | FastAPI HTTP server |
| [`waygate-scheduler`](apps/scheduler/) | Cron job runner |
| [`waygate-plugin-local-storage`](plugins/local-storage/) | Filesystem storage plugin |
| [`waygate-plugin-provider-ollama`](plugins/provider-ollama/) | Ollama LLM provider plugin |
| [`waygate-plugin-webhook-generic`](plugins/webhook-generic/) | Generic webhook ingestion plugin |

## Writing a Plugin

Implement the relevant abstract base class from `waygate-core`, register a `waygate_plugin_config` hookimpl to expose your config schema, and declare the entry point in your `pyproject.toml`. See any plugin under `plugins/` for a working example.

## Contributing

This repository uses [Conventional Commits](https://www.conventionalcommits.org/). All commit messages must follow the `<type>(<scope>): <summary>` format — see [`.github/copilot-instructions.md`](.github/copilot-instructions.md) for the full convention used here.
