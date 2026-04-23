# Consolidated Roadmap

## Purpose

This document carries forward the valuable planning ideas from the legacy docs while updating them to the current repository boundary.

The main rule is simple: roadmap items should extend the current apps, libs, plugin contracts, and storage artifacts. They should not assume packages or services that do not exist in this repo yet.

The original compile workflow proposal is archived at `docs/plans/compile-workflow-original-plan.md`.

## What The Legacy Docs Got Right

The old design set captured several durable principles that are still worth keeping:

- markdown-like stored artifacts should remain the durable knowledge substrate
- plugins should isolate environment-specific integrations from workflow logic
- workflow dispatch should stay transport-agnostic
- human review should remain the fallback when automation cannot safely decide
- future retrieval, graph, and presentation layers should be downstream of the stored corpus, not replacements for it

## Where The Legacy Docs Drifted

The old docs also assumed a larger product surface than the current repository contains.

Those assumptions should not be carried forward as if they already exist:

- there is no full operator UI in this repo beyond the minimal server-rendered control plane in `apps/web`
- there is no retrieval SDK or MCP server package in this repo
- there is no static-site publishing pipeline in this repo
- publish does not currently write to PostgreSQL, pgvector, or any other secondary system

Use the current codebase as the implementation boundary, and treat the rest as future work.

## Roadmap Theme 1: Retrieval Evolution

This theme consolidates the intent behind the older retrieval, hybrid retrieval, graph overlay, and missing-context planning.

### Retrieval baseline in this repo

- the repo publishes structured markdown artifacts to storage
- those artifacts carry useful frontmatter for future downstream use
- there is no retrieval package, search index, or graph traversal layer yet

### Retrieval direction to retain

When retrieval work is added later, it should follow these constraints:

1. published markdown and frontmatter remain the source of truth
2. any lexical, vector, or graph index is reconstructable
3. visibility and other filtering rules apply before downstream results leave the retrieval boundary
4. graph expansion is an augmentation layer, not a replacement for baseline retrieval

### Retrieval update from the legacy plan

The legacy docs often described retrieval as if an SDK and MCP surface already existed. In this repo, that work is still future-facing. The useful part to retain is the source-of-truth and adapter model, not the specific package names or service contracts from the older design set.

## Roadmap Theme 2: Compiler Quality and Trust

This theme consolidates the older structured-consensus and cryptographic-provenance planning.

### Compiler baseline in this repo

- the compile workflow uses one synthesis path and one review path
- rejected drafts retry until a hard revision limit is reached
- repeated failure escalates to human review with a stored review artifact
- publish writes markdown plus frontmatter, but no cryptographic receipt

### Compiler direction to retain

The next quality and trust improvements should extend the current workflow rather than replace it.

Recommended order:

1. add a second review path before attempting multi-draft consensus
2. keep explicit policy-based aggregation rules instead of opaque scoring
3. preserve `publish` and `human_review` as the stable terminal boundaries
4. treat cryptographic provenance as a later, separate concern from review consensus

### Compiler update from the legacy plan

The legacy consensus docs assumed a richer compiler ecosystem than the current repo needs. Today the safest path is still incremental:

- first, extend review depth
- then, consider consensus gates
- only after publish canonicalization is stable, evaluate signed publish receipts

## Roadmap Theme 3: Human-Facing Presentation

This theme consolidates the older thematic synthesis, operator metadata view, static-site publishing, and publish deployment hook planning.

### Presentation baseline in this repo

- the system already writes published markdown with useful frontmatter
- the repo includes a minimal server-rendered control plane in `apps/web`, but there is no human-facing site builder or richer operator workflow UI
- there is no downstream hook consumer for publish events

### Presentation direction to retain

Future presentation work should follow this sequence:

1. treat published markdown as the only authoring source
2. keep thematic synthesis as a separate worker over published content, not a branch inside the ingest-triggered compile flow
3. define a simple metadata presentation contract before building a UI
4. keep publish-triggered rebuilds asynchronous and non-blocking

### Presentation update from the legacy plan

The older docs were right to keep presentation downstream from compilation. The main update is naming and scope:

- use the current `published` namespace instead of the old `live` terminology
- keep site builds, operator views, and deployment hooks outside the core publish node
- do not document a presentation stack as implemented until it exists in this repo

## Roadmap Theme 4: Workflow Orchestration Evolution

This theme captures the planned migration from the current single-graph compile baseline to a supervisor-centered multi-agent workflow.

### Workflow baseline in this repo

- compile is currently a LangGraph workflow with per-document fan-out
- source-document analysis happens independently and is merged later
- synthesis, review, human-review, and publish are explicit workflow boundaries

### Workflow direction to retain

The planned target architecture should preserve the existing durable orchestration boundary while improving multi-document consistency.

Recommended direction:

1. keep LangGraph as the outer workflow layer
2. move compile control toward a central supervisor with specialist subagents
3. replace broad per-document fan-out with stable sequential document analysis
4. split compile context into durable workflow state and transient per-pass prompt context
5. preserve external worker contracts and storage-backed publish outputs during migration

### Workflow update from the current baseline

The important shift is not “use agents everywhere.” It is using a supervisor where compile benefits from centralized orchestration, while still keeping deterministic boundaries for persistence, human review, and publish side effects.

## Recommended Next-Step Framing

If future work resumes on the legacy planning threads, frame them against the current codebase like this:

| Future area                   | Start from                                                          |
| ----------------------------- | ------------------------------------------------------------------- |
| retrieval/search              | published markdown and storage-backed frontmatter                   |
| graph overlay                 | published document ids, source URIs, and other stored relationships |
| missing-context loop          | the existing producer, storage, and workflow boundaries             |
| structured consensus          | the current `synthesis -> review -> publish/human_review` workflow  |
| provenance receipts           | the current publish output plus a canonicalization strategy         |
| thematic or static publishing | published markdown as downstream input                              |

## Legacy Doc Consolidation Map

- `ARCHITECTURE.md`, `DESIGN_SCHEMA.md` -> `architecture.md`, `data-models-and-storage.md`
- `apps.md`, `libs.md`, `plugins.md` -> `architecture.md`, `runtime-and-plugins.md`
- `compile-workflow-spec-initial.md` plus workflow code -> `docs/plans/compile-workflow-original-plan.md`, `ingestion-and-workflows.md`
- `retrieval_model.md`, `hybrid_retrieval_plan.md`, `graph_overlay_plan.md`, `missing_context_loop_plan.md` -> this roadmap under Retrieval Evolution
- `structured_consensus_plan.md`, `cryptographic_provenance_plan.md` -> this roadmap under Compiler Quality and Trust
- `thematic_synthesis_plan.md`, `operator_metadata_view_plan.md`, `static_site_publishing_plan.md`, `publish_deployment_hooks_plan.md` -> this roadmap under Human-Facing Presentation

## Practical Rule For Future Docs

Whenever a new design document is added, mark it explicitly as one of these:

- implemented current behavior
- planned extension to current behavior

That prevents the documentation set from drifting back into a mix of aspirational and already-shipped behavior without clear boundaries.
