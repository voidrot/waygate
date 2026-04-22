# Ingestion And Workflow Pipeline

## Purpose

This document describes the current worker-side workflow behavior implemented in
this repository.

For producer-side transport details, see
`docs/worker_communication_contract.md`.

## Workflow Trigger Contract

The worker entrypoint is `waygate_workflows.router.process_workflow_trigger()`.

Current behavior:

- validates payloads as `WorkflowTriggerMessage`
- handles `draft.ready`
- temporarily ignores deferred events such as `ready.integrate` and unsupported
  events such as `cron.tick`
- returns structured `completed`, `human_review`, `failed`, or `ignored`
  results

Thread ids remain stable:

- `compile:<idempotency_key>` when an idempotency key is present
- otherwise `compile:<sha256(sorted document paths)>`

## Current Compile Workflow

The compile workflow is a real LangGraph workflow in
`waygate_workflows.workflows.compile`.

Its current node sequence is:

1. `normalize_request`
2. `compile_source_document`
3. `synthesis`
4. `review`
5. `publish` or `human_review`

The important change from the earlier baseline is that source analysis is now
sequential, not a broad per-document fan-out.

## Phase Details

### 1. Normalize request

`normalize_request`:

- reads raw documents from storage
- parses them into `SourceDocumentState`
- builds a stable `document_order`
- derives `source_set_key`
- seeds `active_document` with the first parsed document

The source set still requires one complete identity mode across all documents:

- full `content_hash` coverage, producing `hash-<sha256>` over the sorted
  body-content hashes

Mixed or incomplete content-hash coverage is rejected.

### 2. Sequential source analysis

`compile_source_document` runs once per document in stable order.

Each pass builds a transient `DocumentAnalysisPromptContext` from:

- the active document
- relevant prior briefs
- relevant canonical topics and tags
- relevant glossary terms and entities
- relevant claims and references
- relevant unresolved mentions
- optional source-analysis guidance loaded from the `agents` namespace

Prompt context is bounded and reconstructed fresh for each pass.

The current source-analysis supervisor delegates to four specialist tools:

1. metadata extraction
2. narrative summary
3. grounded findings
4. continuity inspection

### 3. Durable compile context updates

After each document pass, durable workflow state is updated with:

- appended metadata and summaries
- `prior_document_briefs`
- `canonical_topics`
- `canonical_tags`
- `glossary`
- `entity_registry`
- `claim_ledger`
- `reference_index`
- `unresolved_mentions`

The workflow now does more than accumulate continuity state. It also resolves
older open mentions when a later document introduces a matching term, entity,
claim, or reference key.

### 4. Optional guidance loading

Source-analysis prompt instructions can be extended by storage-backed guidance
files under the `agents` namespace.

Current lookup paths are:

- `agents/compile/source-analysis/common.md`
- `agents/compile/source-analysis/source-types/<source-type>.md`

Missing guidance files are treated as optional and do not fail the workflow.

### 5. Synthesis

`synthesize_draft` calls the synthesis specialist after the sequential source
analysis loop completes.

The synthesis prompt includes:

- `source_set_key`
- accumulated document summaries
- accumulated metadata
- selected durable compile context such as canonical topics, tags, glossary,
  entity registry, and claim ledger

The resulting markdown body still lives in `DraftGraphState.current_draft`, but the publish boundary now projects that state into a dedicated `DraftDocument` and then into a `CompiledDocument` before rendering.

### 6. Review

`review_draft` keeps the bounded retry behavior:

- approved drafts go to publish
- rejected drafts return to synthesis
- after `MAX_REVISIONS = 3`, the workflow escalates to human review

### 7. Human review

`human_review_gate` writes a review artifact to the `review` namespace and
interrupts with bounded resume actions:

- `resume_to_synthesis`
- `resume_to_publish`

### 8. Publish

`publish_draft` writes the rendered Markdown artifact to:

- `compiled/<compiled_document_hash>.md`

Compiled frontmatter currently includes the compiled artifact id, the source set
key, source document URIs, source content hashes, source provenance fields,
compile time, review feedback, and aggregated metadata.

That frontmatter is now built from the typed `CompiledDocument` contract and rendered through the shared compiled-document template in `waygate-core`.

After the compiled artifact is written, the router emits a follow-on
`ready.integrate` trigger that points at the compiled document URI.

The real integration workflow is still deferred. For now, workers accept and
ignore `ready.integrate` so the trigger contract is live without introducing an
unconsumed transport backlog.

## Current Result Shapes

### Completed draft workflow

```json
{
  "status": "completed",
  "request_key": "compile:draft-123",
  "document_paths": ["file://raw/source.txt"],
  "metadata": {
    "origin": "unit-test"
  },
  "source_set_key": "hash-abc",
  "compiled_document_uri": "file://compiled/compiled-abc.md",
  "compiled_document_id": "compiled-abc",
  "compiled_document_hash": "compiled-abc"
}
```

### Human review interrupt

```json
{
  "status": "human_review",
  "request_key": "compile:draft-789",
  "document_paths": ["file://raw/source.txt"],
  "metadata": {},
  "source_set_key": "hash-review",
  "human_review_record_uri": "file://review/hash-review.json",
  "interrupts": [
    {
      "value": {
        "type": "compile_human_review"
      }
    }
  ]
}
```

### LLM configuration failure

```json
{
  "status": "failed",
  "error_kind": "config",
  "detail": "Unsupported LLM options for provider OllamaProvider",
  "request_key": "compile:draft-config-123",
  "event_type": "draft.ready",
  "document_paths": ["file://raw/source.txt"],
  "metadata": {
    "origin": "unit-test"
  }
}
```

### Unsupported event type

```json
{
  "status": "ignored",
  "event_type": "ready.integrate",
  "document_paths": ["file://compiled/compiled-abc.md"],
  "metadata": {
    "compiled_document_id": "compiled-abc"
  }
}
```

## Current Boundaries

These contracts remain stable in the current implementation:

- `WorkflowTriggerMessage` input shape
- thread id derivation behavior
- `source_set_key` derivation behavior
- review retry and human-review escalation semantics
- human-review resume action shape
- completed, human-review, failed/config, and ignored router results
- raw, review, and compiled artifacts as the durable system of record
