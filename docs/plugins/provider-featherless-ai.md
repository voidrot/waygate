# Featherless AI Provider Plugin

The Featherless AI provider plugin is a first-party WayGate LLM provider implementation for OpenAI-compatible Featherless chat completions.

It uses `langchain-openai` to produce normal and structured runnables for workflow stages such as metadata extraction, draft generation, and review.

## What It Does

- Reads its own plugin config from `WAYGATE_FEATHERLESSAIPROVIDER__*` variables.
- Builds `ChatOpenAI` clients using a Featherless API key and base URL.
- Advertises the common and provider-specific model options supported by Featherless.
- Routes Featherless-only request fields through LangChain's `extra_body` support for OpenAI-compatible backends.
- Provides structured output support through LangChain's `with_structured_output()` wrapper.
- Implements the optional embeddings companion contract for retrieval-oriented consumers.

## Behavior

- The plugin name is `FeatherlessAIProvider`.
- Provider options are filtered against capability metadata before the runnable is built.
- The selected model name comes from the current workflow request.
- `top_k` is supported as a WayGate common option, but is transmitted as a Featherless-specific request field.
- The plugin can remain installed without credentials until it is selected as the active provider; it fails fast on invocation if the API key is missing.

## Configuration

| Variable                                              | Default                         | Description                        |
| ----------------------------------------------------- | ------------------------------- | ---------------------------------- |
| `WAYGATE_FEATHERLESSAIPROVIDER__FEATHERLESS_API_KEY`  | none                            | Featherless API key used for auth. |
| `WAYGATE_FEATHERLESSAIPROVIDER__FEATHERLESS_BASE_URL` | `https://api.featherless.ai/v1` | Base URL of the Featherless API.   |

The core settings also provide the model names used by the workflow stages:

- `WAYGATE_CORE__METADATA_MODEL_NAME`
- `WAYGATE_CORE__DRAFT_MODEL_NAME`
- `WAYGATE_CORE__REVIEW_MODEL_NAME`
- `WAYGATE_CORE__LLM_PLUGIN_NAME=FeatherlessAIProvider`

## Entry Point

- `waygate.plugins.llm`

## Notes

- Featherless uses Bearer API key authentication and an OpenAI-compatible chat completions API.
- The configured base URL should point at the OpenAI-compatible API root, such as `https://api.featherless.ai/v1`, rather than a concrete `/chat/completions` endpoint.
- Featherless-specific tool calling is only documented for some model families, so model choice affects advanced capabilities.
- This plugin intentionally stays on the Chat Completions-compatible path by default instead of enabling Responses API features.
- Embeddings use an explicit embedding model name supplied by the caller rather than the compile workflow's stage model defaults.
