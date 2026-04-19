# WayGate Scheduler

The scheduler app is the recurring-job boundary for WayGate.

It bootstraps the shared runtime, resolves the configured communication client, discovers cron plugins, and registers one APScheduler job per installed plugin.

## What It Does

- Boots the shared WayGate app context.
- Validates that the configured communication client exists before scheduling work.
- Registers cron jobs for installed `CronPlugin` implementations.
- Calls each cron plugin on schedule and forwards a `cron.tick` trigger message.
- Keeps the scheduler loop running until a termination signal arrives.

## Runtime Flow

1. `waygate_scheduler.main()` starts the async scheduler loop.
2. `_run_scheduler()` bootstraps the shared runtime and counts installed cron plugins.
3. The configured communication plugin is resolved eagerly so startup fails fast when misconfigured.
4. Each cron plugin is wrapped in an APScheduler job using its `schedule` expression.
5. The scheduler runs until `SIGINT` or `SIGTERM` is received.

## Entry Point

- `waygate_scheduler:main` starts the scheduler process.

## Configuration

The scheduler reads the shared `WAYGATE_*` settings from `waygate-core`.

Important settings include:

- `WAYGATE_CORE__COMMUNICATION_PLUGIN_NAME`
- the selected communication plugin's own settings
- each cron plugin's `schedule` property

## Notes

- The scheduler dispatches `cron.tick` trigger messages, but the worker-side router still decides what is currently executable.
- Signal handlers are installed when the runtime supports them.
