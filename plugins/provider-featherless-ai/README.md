# waygate-plugin-provider-featherless-ai

WayGate LLM provider plugin backed by [Featherless AI](https://featherless.ai/). It uses `langchain-openai` against Featherless's OpenAI-compatible chat completions API.

It also implements the optional embeddings companion contract for retrieval-oriented consumers that need an OpenAI-compatible embeddings client.

## Installation

```bash
uv add waygate-plugin-provider-featherless-ai
```

The plugin is discovered automatically via its entry point. No code changes are required.

The Featherless API key is only required when this provider is selected as the active WayGate LLM provider.

## Configuration

Settings are read from environment variables under `WAYGATE_FEATHERLESSAIPROVIDER__*`:

| Variable                                              | Default                         | Description                        |
| ----------------------------------------------------- | ------------------------------- | ---------------------------------- |
| `WAYGATE_FEATHERLESSAIPROVIDER__FEATHERLESS_API_KEY`  | none                            | Featherless API key used for auth. |
| `WAYGATE_FEATHERLESSAIPROVIDER__FEATHERLESS_BASE_URL` | `https://api.featherless.ai/v1` | Base URL of the Featherless API.   |

Runtime invocation options are supplied through workflow profiles and request overrides, not separate environment variables per workflow. Supported options:

- Common options: `temperature`, `top_k`, `top_p`, `seed`, `stop`, `max_tokens`
- Featherless provider options: `presence_penalty`, `frequency_penalty`, `repetition_penalty`, `min_p`, `min_tokens`, `stop_token_ids`, `include_stop_str_in_output`

`top_k`, `repetition_penalty`, `min_p`, `min_tokens`, `stop_token_ids`, and `include_stop_str_in_output` are sent through `extra_body` because they are Featherless-specific request fields on an OpenAI-compatible backend.

## Entry Point

```toml
[project.entry-points."waygate.plugins.llm"]
featherless_ai_provider = "waygate_plugin_provider_featherless_ai.plugin:FeatherlessAIProvider"
```

## Model Selection

The models used for different pipeline stages are configured via core settings:

| Variable                            | Default      |
| ----------------------------------- | ------------ |
| `WAYGATE_CORE__METADATA_MODEL_NAME` | `qwen3.5:9b` |
| `WAYGATE_CORE__DRAFT_MODEL_NAME`    | `qwen3.5:9b` |
| `WAYGATE_CORE__REVIEW_MODEL_NAME`   | `hermes3:8b` |

Set `WAYGATE_CORE__LLM_PLUGIN_NAME=FeatherlessAIProvider` to make this provider active.

When active, `WAYGATE_FEATHERLESSAIPROVIDER__FEATHERLESS_API_KEY` must be set or the provider will raise a configuration error before constructing the LangChain client.

Embedding clients are resolved with an explicit embedding model name through the optional provider embeddings contract; they do not currently reuse the metadata, draft, or review stage model settings.

## Notes

- Featherless expects Bearer authentication with your API key.
- The default base URL targets Featherless's OpenAI-compatible `/v1` API root. `ChatOpenAI` appends the chat completions path itself, so do not configure `/chat/completions` here.
- Native tool calling support is model-family dependent in Featherless. Structured output can work through LangChain's `with_structured_output()`, but actual support depends on the selected model.
