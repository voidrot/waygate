# WayGate Plugins

This section documents the first-party plugins shipped with WayGate.

## Plugins

- [Communication HTTP](communication-http.md): HTTP transport for workflow trigger messages.
- [Communication NATS](communication-nats.md): JetStream transport for durable workflow trigger messages.
- [Communication RQ](communication-rq.md): RQ/Redis transport for queued workflow triggers.
- [Local Storage](local-storage.md): Filesystem-backed storage implementation.
- [Provider Featherless AI](provider-featherless-ai.md): Featherless-backed OpenAI-compatible LLM provider.
- [Provider Ollama](provider-ollama.md): Ollama-backed LLM provider.
- [Webhook Agent Session](webhook-agent-session.md): Dedicated completed agent-session ingestion plugin.
- [Webhook Generic](webhook-generic.md): Generic webhook ingestion plugin.

## Common Model

All plugins register through the shared `waygate-core` pluggy runtime.

Most plugins expose two things:

- a plugin implementation class
- an opt-in `waygate_plugin_config()` hook that registers a Pydantic config model

That config model becomes part of the merged `WaygateRootSettings` object and is populated from `WAYGATE_<PLUGIN_NAME>__*` environment variables.

## Related References

- [libs/core](../../libs/core/)
- [docs/design/runtime-and-plugins.md](../design/runtime-and-plugins.md)
- [docs/design/data-models-and-storage.md](../design/data-models-and-storage.md)
