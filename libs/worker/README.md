# waygate-worker

Shared worker runtime helpers for WayGate transports.

## What It Does

- boots the shared WayGate app context for worker processes
- preflights compile LLM readiness before accepting work
- resolves the worker-side transport companion for the selected communication plugin
- runs the existing `waygate_workflows.router.process_workflow_trigger` entrypoint
- ships transport helpers for JetStream and RQ runtimes that communication plugins can call
- keeps long-running JetStream jobs alive with periodic `in_progress()` heartbeats

## Running

```bash
uv run waygate-worker-app
```

`waygate-worker-app` is the app entrypoint for worker execution.
