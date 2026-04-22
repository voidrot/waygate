# Document Artifact Model And Rendering Plan

## Purpose

Capture the implementation sequence for splitting document contracts by artifact type and moving compiled and published rendering into the shared core rendering layer.

## Scope

Included:

- explicit `RawDocument`, `DraftDocument`, `CompiledDocument`, and `PublishedDocument` model boundaries
- dedicated frontmatter models for raw, compiled, and published artifacts
- shared compiled and published templates plus render helpers in `waygate-core`
- workflow publish refactoring to project `DraftGraphState` into typed compiled artifacts before persistence

Excluded from this slice:

- full `ready.integrate` implementation
- production writes to the `published/` namespace
- replacing LangGraph checkpoint state with Pydantic artifact models

## Implementation Order

1. Keep `RawDocument` ingress-only and preserve the raw storage contract.
2. Add typed draft, compiled, and published artifact models in `waygate-core`.
3. Expand template configuration so raw, draft, compiled, and published template names are configurable.
4. Add compiled and published Jinja templates and shared render helpers in `waygate-core`.
5. Refactor workflow publishing so compiled artifacts are built from typed models instead of inline metadata dicts.
6. Update tests, env examples, and design docs so the new rendering surface is discoverable.

## Key Decisions

- `DraftDocument` is a projection helper over workflow state, not a persisted `staging/` artifact.
- `CompiledDocument` maps to the current durable output written to `compiled/`.
- `PublishedDocument` remains future-facing but gets a concrete schema and renderer now so its contract is explicit before the integration workflow lands.
- Rendering belongs in `waygate-core`, because it is an artifact boundary shared across apps, plugins, and workflows.

## Verification

Run these checks during implementation:

1. `python -m pytest libs/core/tests/test_template_loader.py`
2. `python -m pytest libs/workflows/tests/draft/test_compile_workflow.py libs/workflows/tests/draft/test_jobs.py`
3. `python -m pytest apps plugins libs/core/tests libs/workflows/tests` when the shared contract change is ready for broader regression
