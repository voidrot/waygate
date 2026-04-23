# Worker App

`apps/worker-app` is the primary worker process for WayGate.

## Responsibility

- bootstrap the shared WayGate runtime
- validate the active compile LLM configuration at startup
- resolve the worker-side transport companion for `WAYGATE_CORE__COMMUNICATION_PLUGIN_NAME`
- hand accepted trigger payloads to `waygate_workflows.router.process_workflow_trigger`

## Supported Transports

- `communication-nats`: durable JetStream consumer loop
- `communication-rq`: Redis/RQ queue consumer loop
- `communication-http`: HTTP endpoint at `/workflows/trigger`

## Running

```bash
uv run waygate-worker-app
```
