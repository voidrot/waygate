# waygate-core

Core framework library for WayGate. Provides the plugin system, configuration registry, application bootstrap, and structured logging used by all other packages in the monorepo.

## Responsibilities

- **Plugin registry** — discovers and loads plugins from setuptools entry points across five groups: `waygate.plugins.storage`, `waygate.plugins.webhooks`, `waygate.plugins.llm`, `waygate.plugins.cron`, `waygate.plugins.communication`.
- **Config registry** — collects per-plugin Pydantic config schemas via the `waygate_plugin_config` hook and merges them into a single root settings object backed by `pydantic-settings`. All values are read from environment variables under the `WAYGATE_` prefix.
- **Bootstrap** — `bootstrap_app()` is the single entry point for application startup. It runs logging setup, plugin loading, config building, and plugin instantiation in order, returning a frozen `WaygateAppContext`.
- **Hook specs** — defines the pluggy hookspec class (`WayGatePluginSpec`) and exports `hookimpl` for use by plugin packages.
- **Plugin base classes** — abstract base classes for `StoragePlugin`, `WebhookPlugin`, `LLMProviderPlugin`, `CronPlugin`, and `CommunicationClientPlugin`.
- **Database metadata** — first-party SQLAlchemy ORM models for tracked documents, workflow jobs, job transitions, document-job edit history, vector references, and Alembic metadata discovery.

## Database Models

`waygate-core` now exposes the first-party relational metadata used for secondary indexing and workflow observability.

- `DocumentType` defines semantic document taxonomy.
- `Document` is the shared registry for raw, compiled, and published artifacts with searchable metadata facets and audit timestamps.
- `RawDocumentRecord`, `CompiledDocumentRecord`, and `PublishedPageRecord` hold artifact-specific fields that should not leak across boundaries.
- `WorkflowJob` and `WorkflowJobTransition` track job details and state transitions.
- `DocumentJobLink` records every job that edited a document with `edit_type`, `edit_count`, `first_edit_at`, and `last_edit_at`.
- `DocumentVectorRef` stores downstream vector-store references as reconstructable secondary indexes.

These tables are designed to complement storage-backed artifacts rather than replace them. Raw, compiled, and published files remain the source of truth.

The schema is intentionally PostgreSQL-specific and now assumes PostgreSQL 18+ so it can use native `uuid` columns with the built-in `uuidv7()` function for primary key defaults.

## Usage

```python
from waygate_core import bootstrap_app

ctx = bootstrap_app()

# Access merged config (core + all plugin fields)
print(ctx.config.core)
print(ctx.config.local_storage)   # present when waygate-plugin-local-storage is installed

# Access instantiated plugins
storage = ctx.plugins.storage["LocalStoragePlugin"]
llm = ctx.plugins.llm["OllamaProvider"]
```

## Configuration

Core settings are nested under `WAYGATE_CORE__*`:

| Variable                                  | Default                    | Description                        |
| ----------------------------------------- | -------------------------- | ---------------------------------- |
| `WAYGATE_CORE__PG_HOST`                   | `localhost`                | Postgres host                      |
| `WAYGATE_CORE__PG_PORT`                   | `5432`                     | Postgres port                      |
| `WAYGATE_CORE__PG_USER`                   | `postgres`                 | Postgres user                      |
| `WAYGATE_CORE__PG_PASSWORD`               | `postgres`                 | Postgres password                  |
| `WAYGATE_CORE__PG_DB`                     | `postgres`                 | Postgres database                  |
| `WAYGATE_CORE__REDIS_DSN`                 | `redis://localhost:6379/0` | Redis DSN                          |
| `WAYGATE_CORE__STORAGE_PLUGIN_NAME`       | `local-storage`            | Active storage plugin              |
| `WAYGATE_CORE__LLM_PLUGIN_NAME`           | `OllamaProvider`           | Active LLM provider plugin         |
| `WAYGATE_CORE__COMMUNICATION_PLUGIN_NAME` | `communication-http`       | Active communication client plugin |
| `WAYGATE_CORE__TEMPLATE_PACKAGES`         | `waygate_core`             | Comma-separated template packages  |
| `WAYGATE_CORE__RAW_DOC_TEMPLATE`          | `raw_document.j2`          | Raw document template name         |
| `WAYGATE_CORE__COMPILED_DOC_TEMPLATE`     | `compiled_document.j2`     | Compiled document template name    |
| `WAYGATE_CORE__PUBLISHED_DOC_TEMPLATE`    | `published_document.j2`    | Published document template name   |
| `WAYGATE_CORE__METADATA_MODEL_NAME`       | `qwen3.5:9b`               | Model used for metadata extraction |
| `WAYGATE_CORE__DRAFT_MODEL_NAME`          | `qwen3.5:9b`               | Model used for draft generation    |
| `WAYGATE_CORE__REVIEW_MODEL_NAME`         | `hermes3:8b`               | Model used for review              |

The local and Compose example env files set `WAYGATE_CORE__COMMUNICATION_PLUGIN_NAME=communication-nats` for the durable JetStream-backed worker flow.

`WAYGATE_CORE__LLM_WORKFLOW_PROFILES` (default `{}`) accepts a JSON object keyed by workflow name for model and option defaults.

The following aliases are also accepted for backward compatibility:

- `WAYGATE_CORE__REDIS_URL` -> `WAYGATE_CORE__REDIS_DSN`
- `WAYGATE_CORE__RAW_DOCUMENT_TEMPLATE` -> `WAYGATE_CORE__RAW_DOC_TEMPLATE`
- `WAYGATE_CORE__COMPILED_DOCUMENT_TEMPLATE` -> `WAYGATE_CORE__COMPILED_DOC_TEMPLATE`
- `WAYGATE_CORE__PUBLISHED_DOCUMENT_TEMPLATE` -> `WAYGATE_CORE__PUBLISHED_DOC_TEMPLATE`
- `WAYGATE_CORE__METADATA_MODEL` -> `WAYGATE_CORE__METADATA_MODEL_NAME`
- `WAYGATE_CORE__DRAFT_MODEL` -> `WAYGATE_CORE__DRAFT_MODEL_NAME`
- `WAYGATE_CORE__REVIEW_MODEL` -> `WAYGATE_CORE__REVIEW_MODEL_NAME`

Logging is configured with:

- `LOG_LEVEL` (default: `INFO`) sets the minimum structlog level.

Example workflow profile payload for `WAYGATE_CORE__LLM_WORKFLOW_PROFILES`:

```json
{
    "draft": {
        "model_name": "qwen3.5:9b",
        "common_options": {
            "temperature": 0.2,
            "max_tokens": 256
        },
        "provider_options": {
            "OllamaProvider": {
                "num_ctx": 4096
            }
        }
    }
}
```

A `.env` file in the working directory is loaded automatically.

## Writing a Plugin

1. Implement the appropriate abstract base class (`StoragePlugin`, `WebhookPlugin`, etc.).
2. Add a `plugin_name` class attribute matching the name you will register.
3. Implement `waygate_plugin_config()` returning a `PluginConfigRegistration` with your Pydantic config model.
4. Implement the category hook (e.g. `waygate_storage_plugin()`) returning your class.
5. Declare both hookimpls using the `@hookimpl` decorator imported from `waygate_core.plugin.hooks`.
6. Register entry points in `pyproject.toml` under the appropriate `waygate.plugins.*` group.

```python
from waygate_core.plugin.hooks import PluginConfigRegistration, hookimpl
from waygate_core.plugin.storage import StoragePlugin
from pydantic import BaseModel, Field

class MyConfig(BaseModel):
    path: str = Field(default="/data")

class MyStoragePlugin(StoragePlugin):
    plugin_name = "my-storage"

    def __init__(self, config: MyConfig | None = None) -> None:
        self._config = config or MyConfig()

    @staticmethod
    @hookimpl
    def waygate_storage_plugin() -> type["MyStoragePlugin"]:
        return MyStoragePlugin

    @staticmethod
    @hookimpl
    def waygate_plugin_config() -> PluginConfigRegistration:
        return PluginConfigRegistration(name="my-storage", config=MyConfig)
```

```toml
# pyproject.toml
[project.entry-points."waygate.plugins.storage"]
my_storage = "my_package.plugin:MyStoragePlugin"
```

Plugin config is then automatically available as `ctx.config.my_storage` and populated from `WAYGATE_MY_STORAGE__*` environment variables.
