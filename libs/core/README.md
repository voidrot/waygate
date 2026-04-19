# waygate-core

Core framework library for WayGate. Provides the plugin system, configuration registry, application bootstrap, and structured logging used by all other packages in the monorepo.

## Responsibilities

- **Plugin registry** — discovers and loads plugins from setuptools entry points across four groups: `waygate.plugins.storage`, `waygate.plugins.webhooks`, `waygate.plugins.llm`, `waygate.plugins.cron`.
- **Config registry** — collects per-plugin Pydantic config schemas via the `waygate_plugin_config` hook and merges them into a single root settings object backed by `pydantic-settings`. All values are read from environment variables under the `WAYGATE_` prefix.
- **Bootstrap** — `bootstrap_app()` is the single entry point for application startup. It runs logging setup, plugin loading, config building, and plugin instantiation in order, returning a frozen `WaygateAppContext`.
- **Hook specs** — defines the pluggy hookspec class (`WayGatePluginSpec`) and exports `hookimpl` for use by plugin packages.
- **Plugin base classes** — abstract base classes for `StoragePlugin`, `WebhookPlugin`, `LLMProviderPlugin`, and `CronPlugin`.

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

| Variable | Default | Description |
|---|---|---|
| `WAYGATE_CORE__PG_HOST` | `localhost` | Postgres host |
| `WAYGATE_CORE__PG_PORT` | `5432` | Postgres port |
| `WAYGATE_CORE__PG_USER` | `postgres` | Postgres user |
| `WAYGATE_CORE__PG_PASSWORD` | `postgres` | Postgres password |
| `WAYGATE_CORE__PG_DB` | `postgres` | Postgres database |
| `WAYGATE_CORE__REDIS_DSN` | `redis://localhost:6379/0` | Redis DSN |
| `WAYGATE_CORE__STORAGE_PLUGIN_NAME` | `local-storage` | Active storage plugin |
| `WAYGATE_CORE__LLM_PLUGIN_NAME` | `OllamaProvider` | Active LLM provider plugin |

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
