# Ollama LLM Provider Plugin

Implements an `LLMProviderPlugin` backed by Ollama via `langchain_ollama`.

Key file:

- [ollama_provider.py](plugins/ollama_provider/src/waygate_plugin_ollama_provider/ollama_provider.py)

Notes:

- Uses `OLLAMA_BASE_URL` env var to locate a local Ollama server (default: `http://localhost:11434`).
- Provides `get_llm()` and `get_structured_llm()` helpers returning LangChain-compatible LLM objects.
