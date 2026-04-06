# Developer Guide

This guide helps contributors understand where to look and how to add features.

- Code layout: packages are under `apps/`, `libs/`, and `plugins/`.
- Adding a new LLM provider: implement `LLMProviderPlugin` in `libs/core` and register the entry point `waygate.plugins.llm`.
- Adding a storage provider: implement `StorageProvider` and register `waygate.plugins.storage`.

Quick pointers to source locations:

- `apps/compiler` — graph building and execution: [graph.py](apps/compiler/src/compiler/graph.py), [worker.py](apps/compiler/src/compiler/worker.py)
- `libs/core` — LLM abstractions and plugin base: [llm_base.py](libs/core/src/waygate_core/llm_base.py), [plugin_base.py](libs/core/src/waygate_core/plugin_base.py)
- `plugins/storage_local` — example local storage provider: [local_storage.py](plugins/storage_local/src/waygate_plugin_local_storage/local_storage.py)
