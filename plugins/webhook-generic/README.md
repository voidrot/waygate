# waygate-plugin-webhook-generic

WayGate webhook plugin for generic HTTP webhook ingestion. Accepts arbitrary JSON payloads and converts them into `RawDocument` objects for downstream processing. Intended as a starting point and reference implementation for custom webhook integrations.

## Installation

```bash
uv add waygate-plugin-webhook-generic
```

The plugin is discovered automatically via its entry point. No code changes are required.

## Behaviour

- **Payload verification** — passes through without validation by default. Override `verify_webhook_request` in a subclass to add signature checking.
- **Payload enrichment** — returns the payload unchanged by default. Override `enrich_webhook_payload` to add or transform fields before document creation.
- **Document creation** — `handle_webhook` must be implemented by concrete subclasses; the base implementation raises `NotImplementedError`.

## Configuration

This plugin has no configuration of its own. Its presence is registered under `WAYGATE_GENERIC_WEBHOOK__*` but no fields are currently defined.

## Entry Point

```toml
[project.entry-points."waygate.plugins.webhooks"]
generic_webhook = "waygate_plugin_webhook_generic.plugin:GenericWebhookPlugin"
```

## Extending

Subclass `GenericWebhookPlugin` (or implement `WebhookPlugin` directly from `waygate-core`) to handle a specific webhook provider, adding signature verification and payload normalisation as needed.
