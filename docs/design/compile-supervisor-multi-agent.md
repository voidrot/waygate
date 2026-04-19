# Compile Supervisor Multi-Agent Design

## Purpose

This document explains the supervisor-centered compile design as implemented in
this repository.

Unlike the older planned-extension version of this doc, the repository now
contains a working implementation of the sequential supervisor workflow.

## Design Status

Implemented in this repository.

Still pending before merge or release-quality signoff:

- real end-to-end compile validation with a live configured LLM provider
- any additional decomposition of source analysis beyond the current specialist
  set

## Architectural Positioning

The current compile design uses two layers:

1. LangGraph as the durable orchestration layer for persistence, retries,
   interrupts, and deterministic side effects.
2. A LangChain supervisor with specialist subagents for source analysis,
   synthesis, and review.

This keeps compile inside a bounded workflow graph rather than moving to an
unstructured agent loop.

## Pattern Selection

| Pattern             | Use in the current repo      | Why                                                              |
| ------------------- | ---------------------------- | ---------------------------------------------------------------- |
| Subagents           | Primary for source analysis  | Centralized control with specialist delegation                   |
| Custom workflow     | Required                     | Needed for checkpointing, review retries, and interrupts         |
| Handoffs            | Secondary                    | Used for human-review resume boundaries                          |
| Skills and guidance | Partially implemented        | Prompt guidance can now be loaded from the `agents` namespace    |
| Router              | Not used for compile control | Compile needs ongoing orchestration, not one-shot classification |

## Implemented Compile Shape

The current compile flow is:

1. Normalize request and parse all source documents.
2. Build stable `document_order`.
3. For each document in order:
   1. Reconstruct bounded prompt context from durable state and the active
      document.
   2. Run source analysis through the document-analysis supervisor.
   3. Update durable compile context.
   4. Resolve any newly satisfiable unresolved mentions.
4. Run synthesis.
5. Run review.
6. Retry synthesis when review fails and the limit is not reached.
7. Escalate to human review on repeated failure.
8. Publish when approved or explicitly resumed to publish.

## Specialist Roles

The compile agent layout in this repository is:

1. source normalization
2. source analysis
3. synthesis
4. review
5. publish
6. human review

Within source analysis, the current supervisor delegates to four specialist
tools:

1. metadata extraction
2. narrative summary
3. grounded findings
4. continuity inspection

## Durable State Versus Prompt Context

The current implementation enforces the durable-versus-transient split from the migration
plan.

### Durable workflow state

Checkpointed state includes:

- parsed source documents
- document order and cursor
- accumulated metadata and summaries
- prior document briefs
- canonical topics and tags
- glossary
- entity registry
- claim ledger
- reference index
- unresolved mentions
- review and publish state

### Transient per-pass prompt context

Each document-analysis call receives reconstructed prompt context containing:

- the active document
- relevant prior briefs
- relevant canonical topics and tags
- relevant glossary entries and entities
- relevant claims and reference keys
- relevant unresolved mentions
- optional storage-backed guidance instructions

Prompt context is discarded after the pass and rebuilt from durable state for
the next document.

## Guidance Extension Point

The repository now implements the optional later-stage guidance mechanism discussed
in the original plan.

Source-analysis instructions can be extended from the `agents` namespace with:

- `agents/compile/source-analysis/common.md`
- `agents/compile/source-analysis/source-types/<source-type>.md`

This keeps prompt packs aligned with the existing runtime boundary rather than
introducing a separate unmanaged configuration path.

## Continuity Resolution

The current implementation goes beyond simple accumulation of continuity state.

When a later document introduces a matching claim, term, entity, or reference
key, older unresolved mentions can move from `open` to `resolved` in durable
state. This gives the sequential compile loop a real cross-document continuity
benefit instead of only carrying forward prompts.

## Runtime Boundary

The implementation continues to respect the existing app-context boundary:

- LLM providers come from the configured plugin runtime
- storage comes from the configured storage plugin
- workflow behavior depends on merged runtime settings

No provider-specific or storage-specific behavior is hardcoded into the compile
control plane.

## Remaining Follow-Up

The main migration mechanics are implemented in this repository.

Remaining follow-up work is narrower:

- run a real compile end to end with the configured provider stack
- decide whether source analysis should split continuity into finer specialist
  roles
