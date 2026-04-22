# waygate-plugin-provider-ollama

WayGate LLM provider plugin backed by [Ollama](https://ollama.com/). Enables local, self-hosted model inference without requiring an external API key.

It also implements the optional embeddings companion contract for retrieval-oriented consumers that need an Ollama embeddings client.

## Installation

```bash
uv add waygate-plugin-provider-ollama
```

The plugin is discovered automatically via its entry point. No code changes are required. Ollama must be running and reachable at the configured address.

## Configuration

Settings are read from environment variables under `WAYGATE_OLLAMAPROVIDER__*`:

- `WAYGATE_OLLAMAPROVIDER__BASE_URL` defaults to `http://localhost:11434` and should point to the Ollama server root.
- `WAYGATE_OLLAMAPROVIDER__VALIDATE_MODEL_ON_INIT` defaults to `true`. Set it to `false` if you want to defer model availability checks until first invocation.

Runtime invocation options are supplied through workflow profiles and request
overrides, not separate environment variables per workflow. Supported options:

- Common options: `temperature`, `top_k`, `top_p`, `seed`, `stop`, `max_tokens`
- Ollama provider options: `validate_model_on_init`, `num_ctx`, `num_gpu`, `num_thread`, `mirostat`, `mirostat_tau`, `mirostat_eta`,
  `num_predict`, `repeat_last_n`, `repeat_penalty`, `logprobs`, `top_logprobs`, `format`, `reasoning`, `tfs_z`, `keep_alive`

`max_tokens` is mapped to Ollama's `num_predict` when `num_predict` is not
explicitly provided.

Configure `WAYGATE_OLLAMAPROVIDER__BASE_URL` as the Ollama server root, not a concrete `/api/chat` or `/api/generate` endpoint.

## Entry Point

```toml
[project.entry-points."waygate.plugins.llm"]
ollama_provider = "waygate_plugin_provider_ollama.plugin:OllamaProvider"
```

## Model Selection

The models used for different pipeline stages (metadata extraction, drafting, review) are configured via core settings:

| Variable                            | Default      |
| ----------------------------------- | ------------ |
| `WAYGATE_CORE__METADATA_MODEL_NAME` | `qwen3.5:9b` |
| `WAYGATE_CORE__DRAFT_MODEL_NAME`    | `qwen3.5:9b` |
| `WAYGATE_CORE__REVIEW_MODEL_NAME`   | `hermes3:8b` |

Ensure the referenced models are pulled in Ollama before starting the application. The provider validates model availability when the LangChain client is built by default. Set `WAYGATE_OLLAMAPROVIDER__VALIDATE_MODEL_ON_INIT=false` if you need to turn that off and defer failures until the first invocation.

Embedding clients are resolved with an explicit embedding model name through the optional provider embeddings contract; they do not currently reuse the metadata, draft, or review stage model settings.
