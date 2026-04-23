# WayGate Design Docs

This folder consolidates the older planning documents from `waygate-old/docs` into a smaller set of design references that match the current repository.

These documents are intentionally split into two kinds of material:

- current design: architecture and contracts that are implemented in this repository today
- deferred design: roadmap themes that are still useful, but are not implemented in the current repo

Historical planning documents that are useful for background, but do not define current behavior, are archived under `docs/plans/`.

## Read This First

If you are new to the repo, start in this order:

1. `architecture.md`
2. `runtime-and-plugins.md`
3. `ingestion-and-workflows.md`
4. `data-models-and-storage.md`
5. `compile-supervisor-multi-agent.md`
6. `roadmap.md`

## Document Guide

- `architecture.md`: High-level system shape, package boundaries, and the current runtime model.
- `runtime-and-plugins.md`: How bootstrap, plugin discovery, configuration, and app context assembly work.
- `ingestion-and-workflows.md`: How webhook ingestion, cron dispatch, the worker trigger contract, transport adapters, and the compile workflow fit together.
- `data-models-and-storage.md`: Canonical document contracts, published frontmatter, storage namespaces, and URI/path rules.
- `compile-supervisor-multi-agent.md`: Current supervisor-centered multi-agent compile design, with remaining follow-up work called out explicitly.
- `roadmap.md`: Consolidated future-facing design themes carried forward from the legacy docs, updated for the current repo.

## Scope Notes

- These docs describe the repository at its current structure: `apps/web`, `apps/scheduler`, `apps/worker-app`, `libs/core`, `libs/webhooks`, `libs/worker`, `libs/workflows`, and the plugins under `plugins/`.
- `compile-supervisor-multi-agent.md` now documents the implemented sequential supervisor workflow in `libs/workflows`. Read it together with `ingestion-and-workflows.md` for the current compile contract.
- Older documents that described operator UIs, MCP services, retrieval SDK packages, or static-site pipelines are treated here as deferred roadmap material unless the implementation exists in this repo.
- The original compile workflow proposal is archived at `docs/plans/compile-workflow-original-plan.md`. Use it as historical background only; the current implementation contract is documented in `docs/design/ingestion-and-workflows.md`.
- The current migration handoff plan for the supervisor-centered compile workflow is archived at `docs/plans/compile-multi-agent-supervisor-migration-plan.md` and should now be read as historical design context plus follow-up guidance.
- `docs/worker_communication_contract.md` remains useful background for transport expectations, but current workflow behavior should be read from the code in `libs/workflows` and the design docs in this folder.
