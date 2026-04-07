# Generic Webhook Ingestion Plugin

Example ingestion plugin that accepts generic webhook payloads and converts
them into `RawDocument` objects for the receiver to persist.

This plugin is intentionally source-agnostic. It does not infer source-specific
metadata models. If callers need to preserve source metadata, they should pass
an explicit `source_metadata` object in the payload.

Key file:

- [webhook_receiver.py](plugins/webhook_generic/src/waygate_plugin_generic_webhook/webhook_receiver.py)

Testing

- Example HTTP payloads are available in the workspace `tests.rest` file.
