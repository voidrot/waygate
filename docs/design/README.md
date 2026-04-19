# WayGate Design Docs

This folder describes the compile workflow as implemented in the
`compile-supervisor-sequential` worktree.

These documents are intentionally small. They exist to give this branch a local
source of truth for the compile migration work without copying the entire main
repository documentation set into the worktree.

## Read This First

Read these documents in this order:

1. `ingestion-and-workflows.md`
2. `compile-supervisor-multi-agent.md`
3. `../plans/compile-multi-agent-supervisor-migration-plan.md`
4. `../worker_communication_contract.md`

## Document Guide

- `ingestion-and-workflows.md`: current worker-side workflow contract and the
  implemented compile flow in this branch.
- `compile-supervisor-multi-agent.md`: explanation of the supervisor-centered
  compile design as it now exists in code, including remaining follow-up work.
- `../plans/compile-multi-agent-supervisor-migration-plan.md`: historical plan
  and implementation status summary for the migration.
- `../worker_communication_contract.md`: producer-side transport contract
  background for HTTP and RQ communication plugins.

## Scope Notes

- These docs describe the current state of the worktree branch, not the entire
  main repository.
- The code in `libs/workflows` remains the final source of truth for runtime
  behavior when docs and code disagree.
- Live provider validation is intentionally still outside this doc set because
  the branch has not run a real compile end to end yet.
