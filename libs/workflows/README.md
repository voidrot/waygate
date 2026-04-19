# waygate-workflows

Shared workflow entrypoints for WayGate.

This package hosts importable workflow functions that can be executed by worker
runtimes such as RQ. Keeping workflow code here lets producer processes enqueue
jobs by string reference while worker processes import and execute the same code.

## Current scope

- `waygate_workflows.draft.jobs.process_workflow_trigger` handles queued
  `WorkflowTriggerMessage` payloads.
- `draft.ready` currently hands through already-written draft document URIs as
  the minimal boundary for the future draft workflow.
