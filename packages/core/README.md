# WayGate Core Library

## Testing

Run the core package tests from the package directory:

```bash
uv run pytest
```

From the repository root, the equivalent command is:

```bash
mise run test:core
```

Run `mise run uv:sync` from the repository root before running package-local tests
so the workspace packages are installed in editable mode.

## Plugin Contract

WayGate plugins now load through a shared `pluggy` manager in core.

Each plugin package still publishes its provider class through its existing
`waygate.plugins.<type>` Python entry-point group, but the provider class must
also implement the matching pluggy hook:

```python
from waygate_core.plugin import hookimpl


class ExampleWebhookPlugin(WebhookPlugin):
    @staticmethod
    @hookimpl
    def waygate_webhook_plugin() -> type[WebhookPlugin]:
        return ExampleWebhookPlugin
```

Plugins with settings must register config explicitly instead of relying on
provider instantiation side effects. Do not override the provider `config`
property just to participate in config discovery:

```python
from waygate_core.plugin import PluginConfigRegistration, hookimpl


class ExampleStoragePlugin(StoragePlugin):
    @staticmethod
    @hookimpl
    def waygate_plugin_config() -> PluginConfigRegistration:
        return PluginConfigRegistration(
            name="example-storage",
            config=ExampleStorageSettings,
        )
```

Current hook names by plugin type:

- `waygate_webhook_plugin`
- `waygate_storage_plugin`
- `waygate_llm_plugin`
- `waygate_cron_plugin`
- `waygate_plugin_config` for optional settings registration
