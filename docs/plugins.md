# Plugins

Plugins implement concrete providers that conform to the core plugin interfaces.

- `plugins/ollama_provider` — an `LLMProvider` implementation using the Ollama client. See [plugins/ollama_provider README](plugins/ollama_provider/README.md) and [ollama_provider.py](plugins/ollama_provider/src/waygate_plugin_ollama_provider/ollama_provider.py).

- `plugins/storage_local` — local filesystem storage provider; useful for local testing. See [plugins/storage_local README](plugins/storage_local/README.md) and [local_storage.py](plugins/storage_local/src/waygate_plugin_local_storage/local_storage.py).

- `plugins/webhook_generic` — example generic webhook ingestion plugin. See [plugins/webhook_generic README](plugins/webhook_generic/README.md) and [webhook_receiver.py](plugins/webhook_generic/src/waygate_plugin_generic_webhook/webhook_receiver.py).

How to add a plugin

- Implement the appropriate base class from `libs/core` (e.g., `LLMProviderPlugin`, `StorageProvider`, or `IngestionPlugin`).
- Register via entry points in your package's `pyproject.toml` so the registries can discover the provider.
