# Ollama Provider Plugin

The Ollama provider plugin is the first-party LLM provider implementation for WayGate.

It uses the `langchain-ollama` integration to produce normal and structured runnables for workflow stages such as metadata extraction, draft generation, and review.

## What It Does

- Reads its own plugin config from `WAYGATE_OLLAMAPROVIDER__*` variables.
- Advertises the common and provider-specific model options supported by Ollama.
- Maps `max_tokens` to Ollama's `num_predict` when `num_predict` is not explicitly set.
- Can opt into LangChain/Ollama model validation during client construction.
- Provides structured output support through LangChain's `with_structured_output()` wrapper.
- Implements the optional embeddings companion contract for retrieval-oriented consumers.

## Behavior

- The plugin name is `OllamaProvider` and is normalized separately from the environment variable namespace.
- Provider options are filtered against capability metadata before the runnable is built.
- The selected Ollama model name comes from the current workflow request.
- The configured base URL is normalized to the Ollama server root and should not include `/api/chat` or `/api/generate`.

## Configuration

- `WAYGATE_OLLAMAPROVIDER__BASE_URL` defaults to `http://localhost:11434` and should point to the Ollama server root.
- `WAYGATE_OLLAMAPROVIDER__VALIDATE_MODEL_ON_INIT` defaults to `true`. Set it to `false` if you need to skip startup-time model validation and defer failures until invocation.

The core settings also provide the model names used by the workflow stages:

- `WAYGATE_CORE__METADATA_MODEL_NAME`
- `WAYGATE_CORE__DRAFT_MODEL_NAME`
- `WAYGATE_CORE__REVIEW_MODEL_NAME`

## Entry Point

- `waygate.plugins.llm`

## Notes

- Ollama must be running and the referenced models must already be available. Model validation is enabled by default, but you can turn it off when you explicitly want to defer the check until the first invocation.
- This plugin is the default local inference path for the current repository.
- Embeddings use an explicit embedding model name supplied by the caller rather than the compile workflow's stage model defaults.
