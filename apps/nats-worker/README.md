# waygate-nats-worker

JetStream worker process for WayGate workflow triggers.

## Running

```bash
uv run waygate-nats-worker
```

The worker bootstraps the shared WayGate app context, validates the active LLM
provider, ensures the configured JetStream stream and consumers exist, then
pulls `draft.ready` and `cron.tick` messages from NATS and forwards them to the
shared workflow router.
