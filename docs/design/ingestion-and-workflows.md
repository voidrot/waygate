# Ingestion And Workflow Pipeline

## Purpose

This document describes the current worker-side workflow behavior implemented in
 this worktree branch.

For producer-side transport details, see
`docs/worker_communication_contract.md`.

## Workflow Trigger Contract

The worker entrypoint is `waygate_workflows.router.process_workflow_trigger()`.

Current behavior:

- validates payloads as `WorkflowTriggerMessage`
- handles `draft.ready`
- ignores unsupported event types such as `cron.tick`
- returns structured `completed`, `human_review`, or `ignored` results

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

- full `source_hash` coverage, producing `hash-<sha256>`
- or full `source_uri` coverage, producing `uri-<sha256>`

Mixed or incomplete coverage is rejected.

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

- `published/<source_set_key>.md`

Published frontmatter currently includes source ids, source URIs, compile time,
review feedback, and aggregated metadata.

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
  "published_document_uri": "file://published/hash-abc.md",
  "published_document_id": "hash-abc"
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

### Unsupported event type

```json
{
  "status": "ignored",
  "event_type": "cron.tick",
  "document_paths": [],
  "metadata": {}
}
```

## Current Boundaries

These contracts remain stable in the branch:

- `WorkflowTriggerMessage` input shape
- thread id derivation behavior
- `source_set_key` derivation behavior
- review retry and human-review escalation semantics
- human-review resume action shape
- completed, human-review, and ignored router results
- raw, review, and published artifacts as the durable system of record
