# waygate-core

`waygate-core` is the shared runtime library for WayGate. It provides the bootstrap entry point, the merged settings model, the pluggy-based plugin registry, logging helpers, shared document schemas, and the Jinja-backed document rendering utilities used by the apps and plugins in the monorepo.

## What it owns

- Process startup through `bootstrap_app()` and `get_app_context()`.
- Core settings under `WAYGATE_CORE__*`.
- Plugin settings discovered through `waygate_plugin_config()` and exposed as normalized root fields such as `WAYGATE_LOCAL_STORAGE__*`.
- Base classes and DTOs for storage, webhook, cron, LLM provider, and communication plugins.
- Shared document models and template helpers for raw, compiled, and published document rendering.
- Structured logging setup through `configure_logging()` and `get_logger()`.

## Runtime flow

1. `bootstrap_app()` configures logging.
2. The shared plugin manager loads setuptools entry points for all supported plugin groups.
3. `ConfigRegistry` builds a merged `WaygateRootSettings` object from core settings and plugin config models.
4. The plugin manager instantiates the selected plugins with their resolved config objects.
5. The resulting `WaygateAppContext` is memoized by `get_app_context()` for process-wide reuse.

This means core startup is intentionally stateful at the process level. The bootstrap step should be treated as one-time initialization.

## Public surface

### Bootstrap

- `bootstrap_app()` creates the application context.
- `get_app_context()` returns the cached context after first initialization.

### Configuration

- `CoreSettings` holds the built-in configuration fields.
- `LLMWorkflowProfile` captures per-workflow model defaults.
- `WaygateRootSettings` is the merged root settings model returned by the registry.
- `ConfigRegistry` discovers plugin config models and adds them to the root settings object.

Environment variables follow two conventions:

- Core settings use `WAYGATE_CORE__*`.
- Plugin settings use `WAYGATE_<PLUGIN_NAME>__*`, where the plugin name is normalized to lowercase with underscores.

### Plugins

- `WayGatePluginSpec` defines the pluggy hooks.
- `WayGatePluginManager` loads plugin entry points, resolves plugin configs, and instantiates plugins.
- `StoragePlugin`, `WebhookPlugin`, `CronPlugin`, `LLMProviderPlugin`, and `CommunicationClientPlugin` are abstract contracts for extensions.
- `PluginConfigRegistration` is the opt-in mechanism for exposing plugin-specific config.

### LLM helpers

- `LLMInvocationRequest` describes a model invocation.
- `LLMProviderCapabilities` advertises supported options.
- `resolve_invocation_options()` filters or rejects unsupported options depending on policy.

### Documents and templates

- `RawDocument` and `RawDocumentFrontmatter` represent the shared raw-document contract.
- `DraftDocument` represents the validated compile-stage draft artifact projected from workflow state.
- `CompiledDocument` and `CompiledDocumentFrontmatter` represent the durable approved compile artifact.
- `PublishedDocument` and `PublishedDocumentFrontmatter` represent the future corpus-level published artifact.
- `SourceDocumentReference` represents normalized source provenance reused by draft and compiled artifacts.
- `Visibility` defines the supported visibility states.
- `build_raw_document_frontmatter()`, `build_compiled_document_frontmatter()`, and `build_published_document_frontmatter()` build artifact-specific frontmatter models.
- `render_raw_document()`, `render_draft_document()`, `render_compiled_document()`, and `render_published_document()` provide the shared rendering path.

### Logging

- `configure_logging()` installs the structlog pipeline.
- `get_logger()` returns a structured logger instance.

## Extension points

To add a new plugin, implement the relevant abstract base class, add a `waygate_plugin_config()` hook if the plugin has settings, and register the class under the appropriate entry-point group in `pyproject.toml`.

Common plugin groups are:

- `waygate.plugins.storage`
- `waygate.plugins.webhooks`
- `waygate.plugins.llm`
- `waygate.plugins.cron`
- `waygate.plugins.communication`

## Notes

- The template loader caches package and template resolution in process memory.
- `WayGatePluginManager.get_plugins()` keys the returned mapping by each plugin instance’s `name` property, not by entry-point name.
- `get_app_context()` memoizes the whole application context, so code using it should assume process-wide state.

## Related files

- [libs/core/src/waygate_core/bootstrap.py](../../libs/core/src/waygate_core/bootstrap.py)
- [libs/core/src/waygate_core/config/registry.py](../../libs/core/src/waygate_core/config/registry.py)
- [libs/core/src/waygate_core/config/schema.py](../../libs/core/src/waygate_core/config/schema.py)
- [libs/core/src/waygate_core/plugin/registry.py](../../libs/core/src/waygate_core/plugin/registry.py)
- [libs/core/src/waygate_core/plugin/hooks.py](../../libs/core/src/waygate_core/plugin/hooks.py)
- [libs/core/src/waygate_core/files/template.py](../../libs/core/src/waygate_core/files/template.py)
- [libs/core/src/waygate_core/logging/config.py](../../libs/core/src/waygate_core/logging/config.py)
- [libs/core/src/waygate_core/logging/helpers.py](../../libs/core/src/waygate_core/logging/helpers.py)
- [libs/core/src/waygate_core/schema/document.py](../../libs/core/src/waygate_core/schema/document.py)
