# waygate-worker-app

Primary transport-agnostic worker app for WayGate workflow triggers.

## Running

```bash
uv run waygate-worker-app
```

The app bootstraps the shared WayGate runtime, preflights the active compile
LLM configuration, resolves the worker-side transport companion for
`WAYGATE_CORE__COMMUNICATION_PLUGIN_NAME`, and starts the matching listener.
