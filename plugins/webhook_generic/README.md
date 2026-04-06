# Generic Webhook Ingestion Plugin

Example ingestion plugin that accepts generic webhook payloads and converts
them into `RawDocument` objects for the receiver to persist.

Key file:

- [webhook_receiver.py](plugins/webhook_generic/src/waygate_plugin_generic_webhook/webhook_receiver.py)

Testing

- Example HTTP payloads are available in the workspace `tests.rest` file.
