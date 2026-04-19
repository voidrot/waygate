# Runtime and Plugin Model

## Purpose

This document explains how WayGate assembles its runtime at startup and how first-party and third-party plugins fit into that model.

## Bootstrap Sequence

`bootstrap_app()` in `waygate-core` is the single startup entrypoint used across the repo.

It performs three phases:

1. configure logging
2. load all installed plugins and discover their config schemas
3. build merged settings and instantiate plugins grouped by category

The result is a frozen `WaygateAppContext` with two top-level parts:

- `config`: the merged `WaygateRootSettings`
- `plugins`: grouped plugin instances for storage, webhooks, llm, cron, and communication

`get_app_context()` caches that context process-wide so long-running services can reuse the same initialized runtime.

## Plugin Categories

WayGate defines five plugin groups.

| Group                           | Hook                                  | Purpose                                                                      | First-party packages in this repo                                      |
| ------------------------------- | ------------------------------------- | ---------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| `waygate.plugins.storage`       | `waygate_storage_plugin`              | Persistent document storage and namespace handling                           | `waygate-plugin-local-storage`                                         |
| `waygate.plugins.webhooks`      | `waygate_webhook_plugin`              | Inbound payload verification, enrichment, and normalization to `RawDocument` | `waygate-plugin-webhook-generic`                                       |
| `waygate.plugins.llm`           | `waygate_llm_provider_plugin`         | LLM invocation for workflow stages                                           | `waygate-plugin-provider-ollama`                                       |
| `waygate.plugins.cron`          | `waygate_cron_plugin`                 | Scheduled job sources for the scheduler                                      | none currently shipped                                                 |
| `waygate.plugins.communication` | `waygate_communication_client_plugin` | Transport-specific delivery of workflow triggers                             | `waygate-plugin-communication-http`, `waygate-plugin-communication-rq` |

## Configuration Registry

Plugins opt in to configuration discovery by implementing `waygate_plugin_config()` and returning a `PluginConfigRegistration`.

That registration controls two things:

1. the field added to the merged settings object
2. the environment variable namespace used to populate it

Name normalization is deliberate:

- plugin name `local-storage` becomes settings field `local_storage`
- its environment variables use `WAYGATE_LOCAL_STORAGE__*`

Core settings remain under `WAYGATE_CORE__*`.

The merged settings object is built with these runtime rules:

- prefix: `WAYGATE_`
- nested delimiter: `__`
- env file: `.env`
- unknown fields: ignored

This keeps plugin configuration discoverable without requiring each app to maintain separate settings models.

## Runtime Selection

Core settings decide which installed plugin instance is active for a given role.

Examples:

- `WAYGATE_CORE__STORAGE_PLUGIN_NAME`
- `WAYGATE_CORE__LLM_PLUGIN_NAME`
- `WAYGATE_CORE__COMMUNICATION_PLUGIN_NAME`

The runtime fails fast when a configured communication plugin is missing. It does not silently pick a random transport unless an explicit fallback path is allowed by the caller.

## First-Party Plugin Roles

### Local storage

- Owns the default filesystem-backed document store.
- Creates and manages the `raw`, `staging`, `review`, `published`, `metadata`, `templates`, and `agents` namespaces.
- Returns base-relative `file://` URIs for stored documents.

### Generic webhook

- Provides a concrete webhook reference implementation.
- Validates a structured JSON payload and maps each incoming document to a `RawDocument`.
- Leaves request verification permissive by default so it can be subclassed for provider-specific production integrations.

### Communication HTTP and RQ

- Implement the same `submit_workflow_trigger()` contract.
- Let producers dispatch work without knowing whether delivery is an HTTP POST or an RQ enqueue operation.

### Ollama provider

- Supplies the current first-party LLM provider implementation used by workflow stages.

## Planned Agent Runtime Boundary

The planned supervisor-centered compile architecture should continue to respect the existing runtime boundary.

That means the supervisor and any specialist agents should still resolve capabilities through the shared `WaygateAppContext` rather than hardcoding provider, storage, or transport assumptions.

In practice, that means:

- LLM access still comes from the configured LLM plugin
- durable artifacts still flow through the configured storage plugin
- workflow behavior still depends on merged runtime settings rather than embedded constants

If prompt packs, templates, or future skills are added later, they should align with the existing `templates` and `agents` namespaces rather than inventing a separate unmanaged configuration path.

## Plugin Authoring Contract

To add a plugin, follow the existing pattern:

1. implement the correct abstract base class from `waygate-core`
2. set a stable plugin name
3. expose config with `waygate_plugin_config()` when settings are needed
4. expose the category hook for the plugin type
5. register the entry point under the appropriate `waygate.plugins.*` group in `pyproject.toml`

That is enough for the core runtime to discover, configure, and instantiate the plugin without app-specific wiring.

## Why This Model Exists

The plugin system is not only an extensibility mechanism. It is also the main architectural boundary between product-specific workflow logic and environment-specific integrations.

That separation gives WayGate three useful properties:

- apps stay small because they ask for capabilities instead of constructing them
- workflow code can assume normalized interfaces instead of transport or provider details
- first-party plugins act as reference implementations for future extensions
