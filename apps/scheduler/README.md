# waygate-scheduler

Background job runner for WayGate. Bootstraps plugin context, validates communication plugin availability, and schedules recurring cron jobs for installed `CronPlugin` implementations.

## Running

```bash
uv run waygate-scheduler
```

All `WAYGATE_*` environment variables are read — see [`waygate-core`](../../libs/core/) for the full reference.

## Extending

Implement `CronPlugin` from `waygate-core` and register it under the `waygate.plugins.cron` entry point group. The scheduler discovers registered cron plugins at startup and schedules them using each plugin's `schedule` cron expression.

Communication client plugins register under `waygate.plugins.communication` and can be selected with `WAYGATE_CORE__COMMUNICATION_PLUGIN_NAME`.
