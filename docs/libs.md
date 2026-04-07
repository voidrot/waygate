# Libraries

Shared libraries used across apps and plugins.

- `libs/core` — core helpers, LLM abstractions, plugin base classes, schemas.
  - Key modules: [waygate_core/llm_base.py](libs/core/src/waygate_core/llm_base.py), [llm_registry.py](libs/core/src/waygate_core/llm_registry.py), [schemas.py](libs/core/src/waygate_core/schemas.py), [plugin_base.py](libs/core/src/waygate_core/plugin_base.py)

- `libs/agent_sdk` — internal retrieval SDK for loading live documents, applying visibility policy, scoring results, and assembling briefings.
  - Key modules: [models.py](libs/agent_sdk/src/waygate_agent_sdk/models.py), [repository.py](libs/agent_sdk/src/waygate_agent_sdk/repository.py), [policy.py](libs/agent_sdk/src/waygate_agent_sdk/policy.py), [scoring.py](libs/agent_sdk/src/waygate_agent_sdk/scoring.py)

- `libs/storage` — storage provider interfaces and registry.
  - Key modules: [storage_base.py](libs/storage/src/waygate_storage/storage_base.py), [storage_registry.py](libs/storage/src/waygate_storage/storage_registry.py)
