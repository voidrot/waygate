# Compiler

The Compiler package builds and executes workflow graphs used to transform
and publish documents. It is responsible for composing node-based workflows
and invoking them with an initial `GraphState`.

Key files and locations:

- [config.py](apps/compiler/src/compiler/config.py) — runtime configuration and storage provider discovery.
- [graph.py](apps/compiler/src/compiler/graph.py) — graph construction and node wiring.
- [worker.py](apps/compiler/src/compiler/worker.py) — graph execution entrypoint (`execute_graph`).
- [maintenance.py](apps/compiler/src/compiler/maintenance.py) — explicit maintenance sweep entrypoint (`waygate-maintenance-sweep`).
- [state.py](apps/compiler/src/compiler/state.py) — runtime state model used during execution.
- Nodes: [draft.py](apps/compiler/src/compiler/nodes/draft.py), [review.py](apps/compiler/src/compiler/nodes/review.py), [publish.py](apps/compiler/src/compiler/nodes/publish.py)

Usage

This package is intended to be executed by the top-level tooling in this
workspace. For local development, import `execute_graph` from
`apps.compiler.src.compiler.worker` and call it with an initial state dict.

For an explicit maintenance sweep over the current storage backend, run:

- `uv run waygate-maintenance-sweep`
- `mise run maintenance:sweep`

To detect stale live documents and enqueue recompilation jobs for stale or hash-mismatch findings during the sweep:

- `uv run waygate-maintenance-sweep --stale-after-hours 24 --enqueue-recompilation`
- `mise run maintenance:sweep -- --stale-after-hours 24 --enqueue-recompilation`

To replay persisted context-error findings that include lineage-backed recompilation signals:

- `uv run waygate-maintenance-sweep --enqueue-recompilation --include-context-errors`
- `mise run maintenance:sweep -- --enqueue-recompilation --include-context-errors`

To archive orphan-lineage live documents in place and prepend a deprecation notice:

- `uv run waygate-maintenance-sweep --archive-orphans`
- `mise run maintenance:sweep -- --archive-orphans`
