# WayGate Core

`libs/core` contains the foundation for plugins and LLM integrations used by
the rest of the workspace. It exposes base classes, registries, schemas, and
small helpers for documentation and templating.

Key modules:

- [llm_base.py](libs/core/src/waygate_core/llm_base.py) — `LLMProviderPlugin` base class.
- [llm_registry.py](libs/core/src/waygate_core/llm_registry.py) — discovery and instantiation of LLM providers.
- [plugin_base.py](libs/core/src/waygate_core/plugin_base.py) — ingestion plugin base types and `RawDocument` definitions.
- [schemas.py](libs/core/src/waygate_core/schemas.py) — pydantic schemas and types.
- [doc_helpers.py](libs/core/src/waygate_core/doc_helpers.py), [file_templates.py](libs/core/src/waygate_core/file_templates.py) — helpers for generating content artifacts.

Contributing

When adding a provider or plugin implement the appropriate base class and
register an entry point so the registry can auto-discover your implementation.
