# waygate-workflows

`waygate-workflows` is the workflow runtime library for WayGate. It owns the
worker-side trigger router, the LangGraph compile workflow, the sequential
source-analysis loop, the publish and human-review boundaries, and the helper
code that reconstructs prompt context from durable workflow state.

## What it owns

- Worker-side trigger handling through `process_workflow_trigger()`.
- Draft compile graph assembly through `compile_workflow()`.
- Source normalization and source-set identity derivation.
- Sequential source-analysis passes under supervisor-controlled specialist
  agents.
- Durable compile context including topics, tags, glossary entries, entity
  registry, claim ledger, reference index, and unresolved mentions.
- Synthesis, review retry, human-review interrupt, and publish boundaries.
- Publish rendering and human-review artifact generation.

## Runtime flow

1. `process_workflow_trigger()` validates an incoming `WorkflowTriggerMessage`.
2. The router builds a stable thread id and initial `DraftGraphState`.
3. `compile_workflow()` runs the LangGraph draft workflow with Postgres-backed
   checkpointing.
4. `normalize_compile_request()` reads raw documents, parses frontmatter, builds
   `document_order`, and derives `source_set_key`.
5. `compile_source_document()` runs one source-analysis pass at a time until all
   source documents have been processed.
6. `synthesize_draft()` produces the candidate markdown page.
7. `review_draft()` approves, rejects for retry, or escalates to human review.
8. `human_review_gate()` writes a review artifact and interrupts when retries
   are exhausted.
9. `publish_draft()` renders the final markdown artifact and writes it to the
   `published` namespace.

## Compile workflow diagram

```mermaid
flowchart TD
    A[workflow trigger] --> B[normalize_request]
    B --> C[compile_source_document]
    C --> D{more source documents?}
    D -- yes --> C
    D -- no --> E[synthesis]
    E --> F[review]
    F --> G{approved?}
    G -- yes --> H[publish]
    G -- no --> I{revision_count >= MAX_REVISIONS?}
    I -- no --> E
    I -- yes --> J[human_review]
    J --> K{resume action}
    K -- resume_to_synthesis --> E
    K -- resume_to_publish --> H
    H --> L[end]
```

## Source-analysis loop

The compile workflow no longer uses the older broad per-document fan-out shape.
Instead, it processes source documents in a stable order so later passes can
reuse durable discoveries from earlier ones.

Each source-analysis pass reconstructs a bounded `DocumentAnalysisPromptContext`
containing:

- the active document
- relevant prior document briefs
- relevant canonical topics and tags
- relevant glossary and entity registry entries
- relevant claim and reference subsets
- relevant unresolved mentions
- optional storage-backed guidance loaded from the `agents` namespace

The current source-analysis supervisor coordinates four specialist roles:

- metadata extraction
- narrative summary
- grounded findings
- continuity inspection

## Durable state model

The main state container is `DraftGraphState` in
`libs/workflows/src/waygate_workflows/schema.py`.

Important durable fields include:

- `source_documents`, `document_order`, `document_cursor`, and `active_document`
- `source_set_key`
- `extracted_metadata` and `document_summaries`
- `prior_document_briefs`
- `canonical_topics` and `canonical_tags`
- `glossary`
- `entity_registry`
- `claim_ledger`
- `reference_index`
- `unresolved_mentions`
- `current_draft`, `review_feedback`, `review_outcome`, and publish fields

The compile node also performs cross-document continuity resolution. When a
later document introduces a matching term, entity, claim, or reference key,
older unresolved mentions can be moved from `open` to `resolved`.

## Public surface

### Router and entrypoints

- `process_workflow_trigger()` is the worker-facing entrypoint.
- `trigger_draft_workflow_from_message()` is the RQ-oriented adapter in
  `draft/jobs.py`.

### Graph assembly

- `compile_workflow()` compiles the LangGraph draft workflow.
- Node modules under `waygate_workflows.nodes` implement the deterministic graph
  boundaries.

### Agent layer

- `normalize_source_documents()` reads and normalizes raw documents.
- `analyze_source_document()` runs the source-analysis supervisor.
- `synthesize_draft_with_specialist()` produces the draft.
- `review_draft_with_specialist()` performs structured review.
- `render_publish_artifact()` builds the publishable markdown artifact.
- `build_human_review_record()` builds the persisted human-review artifact.

### Shared helpers

- `tools.documents` parses source documents and derives `source_set_key`.
- `tools.guidance` loads optional guidance text from the `agents` namespace.
- `tools.publishing` renders the published document with frontmatter.
- `tools.llm` resolves provider-backed model invocations.
- `resolve_storage()` resolves the active storage plugin.

## Trigger handling and outcomes

The worker router currently treats `draft.ready` as the implemented workflow
entrypoint.

- `draft.ready` runs the compile workflow.
- `cron.tick` is still ignored by the default workflow router.

The router returns one of three result shapes:

- `completed` with `published_document_uri` and `published_document_id`
- `human_review` with `human_review_record_uri` and interrupt payload
- `ignored` for unsupported event types

## Storage boundaries

The workflow uses storage namespaces as its durable system-of-record boundary.

- Raw source documents are read from the trigger-provided URIs.
- Human-review artifacts are written to the `review` namespace.
- Published markdown is written to the `published` namespace.
- Optional prompt guidance is read from the `agents` namespace.

## Related files

- [libs/workflows/src/waygate_workflows/router.py](../../libs/workflows/src/waygate_workflows/router.py)
- [libs/workflows/src/waygate_workflows/workflows/compile.py](../../libs/workflows/src/waygate_workflows/workflows/compile.py)
- [libs/workflows/src/waygate_workflows/nodes/compile_source_document.py](../../libs/workflows/src/waygate_workflows/nodes/compile_source_document.py)
- [libs/workflows/src/waygate_workflows/schema.py](../../libs/workflows/src/waygate_workflows/schema.py)
- [docs/design/ingestion-and-workflows.md](../design/ingestion-and-workflows.md)
- [docs/design/compile-supervisor-multi-agent.md](../design/compile-supervisor-multi-agent.md)
