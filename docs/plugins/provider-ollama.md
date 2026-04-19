# Ollama Provider Plugin

The Ollama provider plugin is the first-party LLM provider implementation for WayGate.

It uses the `langchain-ollama` integration to produce normal and structured runnables for workflow stages such as metadata extraction, draft generation, and review.

## What It Does

- Reads its own plugin config from `WAYGATE_OLLAMAPROVIDER__*` variables.
- Advertises the common and provider-specific model options supported by Ollama.
- Maps `max_tokens` to Ollama's `num_predict` when `num_predict` is not explicitly set.
- Provides structured output support through LangChain's `with_structured_output()` wrapper.

## Behavior

- The plugin name is `OllamaProvider` and is normalized separately from the environment variable namespace.
- Provider options are filtered against capability metadata before the runnable is built.
- The selected Ollama model name comes from the current workflow request.

## Configuration

| Variable                           | Default                  | Description                    |
| ---------------------------------- | ------------------------ | ------------------------------ |
| `WAYGATE_OLLAMAPROVIDER__BASE_URL` | `http://localhost:11434` | Base URL of the Ollama server. |

The core settings also provide the model names used by the workflow stages:

- `WAYGATE_CORE__METADATA_MODEL_NAME`
- `WAYGATE_CORE__DRAFT_MODEL_NAME`
- `WAYGATE_CORE__REVIEW_MODEL_NAME`

## Entry Point

- `waygate.plugins.llm`

## Notes

- Ollama must be running and the referenced models must already be available.
- This plugin is the default local inference path for the current repository.
# Ollama Provider Plugin

The Ollama provider plugin is the first-party LLM provider implementation for WayGate.

It uses the `langchain-ollama` integration to produce normal and structured runnables for workflow stages such as metadata extraction, draft generation, and review.

## What It Does

- Reads its own plugin config from `WAYGATE_OLLAMAPROVIDER__*` variables.
- Advertises the common and provider-specific model options supported by Ollama.
- Maps `max_tokens` to Ollama's `num_predict` when `num_predict` is not explicitly set.
- Provides structured output support through LangChain's `with_structured_output()` wrapper.

## Behavior

- The plugin name is `OllamaProvider` and is normalized separately from the environment variable namespace.
- Provider options are filtered against capability metadata before the runnable is built.
- The selected Ollama model name comes from the current workflow request.

## Configuration

| Variable                           | Default                  | Description                    |
| ---------------------------------- | ------------------------ | ------------------------------ |
| `WAYGATE_OLLAMAPROVIDER__BASE_URL` | `http://localhost:11434` | Base URL of the Ollama server. |

The core settings also provide the model names used by the workflow stages:

- `WAYGATE_CORE__METADATA_MODEL_NAME`
- `WAYGATE_CORE__DRAFT_MODEL_NAME`
- `WAYGATE_CORE__REVIEW_MODEL_NAME`

## Entry Point

- `waygate.plugins.llm`

## Notes

- Ollama must be running and the referenced models must already be available.
- This plugin is the default local inference path for the current repository.
