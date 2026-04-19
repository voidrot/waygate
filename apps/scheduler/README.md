# waygate-scheduler

Background job runner for WayGate. Executes cron-style workflows driven by installed `CronPlugin` implementations.

## Running

```bash
uv run waygate-scheduler
```

All `WAYGATE_*` environment variables are read — see [`waygate-core`](../../libs/core/) for the full reference.

## Extending

Implement `CronPlugin` from `waygate-core` and register it under the `waygate.plugins.cron` entry point group. The scheduler will discover and run it automatically at startup.
