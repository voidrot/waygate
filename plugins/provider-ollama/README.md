# waygate-plugin-provider-ollama

WayGate LLM provider plugin backed by [Ollama](https://ollama.com/). Enables local, self-hosted model inference without requiring an external API key.

## Installation

```bash
uv add waygate-plugin-provider-ollama
```

The plugin is discovered automatically via its entry point. No code changes are required. Ollama must be running and reachable at the configured address.

## Configuration

Settings are read from environment variables under `WAYGATE_OLLAMAPROVIDER__*`:

| Variable                           | Default                  | Description                   |
| ---------------------------------- | ------------------------ | ----------------------------- |
| `WAYGATE_OLLAMAPROVIDER__BASE_URL` | `http://localhost:11434` | Base URL of the Ollama server |

Runtime invocation options are supplied through workflow profiles and request
overrides, not separate environment variables per workflow. Supported options:

- Common options: `temperature`, `top_k`, `top_p`, `seed`, `stop`, `max_tokens`
- Ollama provider options: `num_ctx`, `mirostat`, `mirostat_tau`, `mirostat_eta`,
  `num_predict`, `repeat_last_n`, `repeat_penalty`, `tfs_z`, `keep_alive`

`max_tokens` is mapped to Ollama's `num_predict` when `num_predict` is not
explicitly provided.

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

Ensure the referenced models are pulled in Ollama before starting the application.
