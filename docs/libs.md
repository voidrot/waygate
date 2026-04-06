# Libraries

Shared libraries used across apps and plugins.

- `libs/core` — core helpers, LLM abstractions, plugin base classes, schemas.
  - Key modules: [waygate_core/llm_base.py](libs/core/src/waygate_core/llm_base.py), [llm_registry.py](libs/core/src/waygate_core/llm_registry.py), [schemas.py](libs/core/src/waygate_core/schemas.py), [plugin_base.py](libs/core/src/waygate_core/plugin_base.py)

- `libs/storage` — storage provider interfaces and registry.
  - Key modules: [storage_base.py](libs/storage/src/waygate_storage/storage_base.py), [storage_registry.py](libs/storage/src/waygate_storage/storage_registry.py)
