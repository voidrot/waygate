# Single Worker App Layout Plan

## Document Type

Implementation plan.

## Audience

Maintainers working on worker runtime packaging, plugin boundaries, and deployment topology.

## Goal

Replace the transport-specific worker apps with one worker app whose behavior is selected entirely by the configured communication plugin.

## Status

Completed. `apps/worker-app` is now the only worker app package in the repository.

## Current State

- `apps/worker-app` is the only worker app package in the repository.
- `libs/worker` owns shared worker bootstrap, LLM readiness preflight, and workflow handoff.
- `communication-rq`, `communication-nats`, and `communication-http` expose worker-side companions through `waygate_worker_transport_plugin`.

## Target Layout

### Apps

- `apps/worker-app`
  Purpose: the only long-running worker app.
  Script: `waygate-worker-app`.
  Behavior: calls `waygate_worker.run_worker()` with no transport override so `WAYGATE_CORE__COMMUNICATION_PLUGIN_NAME` is authoritative.

### Libraries

- `libs/worker`
  Owns:
  - generic worker bootstrap
  - workflow trigger handoff
  - transport helper code for RQ and NATS
  - worker-facing tests

- `libs/core`
  Owns:
  - communication client contract for producers
  - communication worker transport contract for consumers
  - plugin resolution and runtime context wiring

### Plugins

- `plugins/communication-rq`
  Owns:
  - producer enqueue behavior
  - RQ worker transport registration

- `plugins/communication-nats`
  Owns:
  - JetStream publish behavior
  - NATS worker transport registration

- `plugins/communication-http`
  Owns:
  - producer HTTP dispatch behavior
  - HTTP worker transport registration

## Dependency Changes

### Target app dependency shape

`apps/worker-app` should depend on:

- `waygate-worker`
- the communication plugin packages the deployment intends to support
- storage and LLM provider plugins needed by the workflow runtime

The worker app should not depend directly on `redis`, `rq`, or `nats-py` unless they are required outside the worker library or transport plugins.

### Legacy wrapper cleanup

Completed:

1. add `apps/worker-app`
2. switch compose and deployment entrypoints to the new app
3. remove the transport-specific wrapper packages

### Plugin dependency rule

Communication plugins that expose worker transports should depend on `waygate-worker`.

That keeps the direction of dependencies stable:

- `waygate-worker` depends on `waygate-core` and `waygate-workflows`
- communication plugins depend on `waygate-core` and optionally `waygate-worker`
- the worker app depends on `waygate-worker` plus installed plugins

## Rollout Steps

1. Add the new worker app with no preferred transport override.
2. Update compose and deployment assets to use the single worker app.
3. Validate RQ and NATS paths with the same workflow-trigger fixtures.
4. Add HTTP worker transport support.
5. Remove the legacy wrapper apps.

## Validation Checklist

- `apps/worker-app` starts correctly with `WAYGATE_CORE__COMMUNICATION_PLUGIN_NAME=communication-rq`
- `apps/worker-app` starts correctly with `WAYGATE_CORE__COMMUNICATION_PLUGIN_NAME=communication-nats`
- `apps/worker-app` starts correctly with `WAYGATE_CORE__COMMUNICATION_PLUGIN_NAME=communication-http`
- startup still fails fast on LLM readiness errors before work is accepted
- RQ still enqueues the shared worker job entrypoint
- JetStream still preserves ACK, NAK, TERM, and in-progress heartbeat behavior
- compose and docs refer to the single worker app once migration is complete

## Open Questions

1. Whether the single worker app should install all first-party communication plugins or rely on deployment-specific package sets.
