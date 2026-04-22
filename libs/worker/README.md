# waygate-worker

Shared worker runtime helpers for WayGate transports.

## What It Does

- boots the shared WayGate app context for worker processes
- preflights compile LLM readiness before accepting work
- manages JetStream stream and consumer configuration for NATS-based workers
- runs the existing `waygate_workflows.router.process_workflow_trigger` entrypoint
- keeps long-running JetStream jobs alive with periodic `in_progress()` heartbeats

## Running Through The NATS Worker App

```bash
uv run waygate-nats-worker
```

The `waygate-nats-worker` app is the thin CLI wrapper around this library.
