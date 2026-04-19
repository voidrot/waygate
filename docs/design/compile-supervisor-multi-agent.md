# Compile Supervisor Multi-Agent Design

## Purpose

This document describes the planned target architecture for evolving WayGate's compile workflow into a supervisor-centered multi-agent workflow.

This is a planned extension to current behavior. The current implementation baseline remains documented in [docs/design/ingestion-and-workflows.md](./ingestion-and-workflows.md).

## Design Status

Planned extension. Not currently implemented.

## Why This Change Exists

The current compile workflow fans out per-document analysis and merges the results later. That works as a first baseline, but it creates a context boundary between documents.

The target design changes that tradeoff. It prioritizes consistency across documents by processing them in a stable order so that each later analysis step can inherit prior discoveries.

The main benefits are:

- more consistent topic naming
- more consistent tag assignment
- shared glossary development across the source set
- better handling of cross-document references
- less need for each document pass to rediscover the same concepts from scratch

## Architectural Positioning

The target design should combine two layers:

1. LangGraph as the outer orchestration layer for persistence, retries, interrupts, and deterministic side-effect boundaries.
2. A LangChain supervisor with specialist subagents as the inner compile-control layer.

This means WayGate is not moving to a free-form agent loop. It is moving to a more structured agentic control plane inside the existing durable workflow boundary.

## Pattern Selection

| Pattern         | Use in WayGate compile | Why                                                            |
| --------------- | ---------------------- | -------------------------------------------------------------- |
| Subagents       | Primary                | Best fit for centralized compile control                       |
| Custom workflow | Required               | Needed for persistence, interrupts, and terminal-state clarity |
| Handoffs        | Secondary              | Useful for human review or operator remediation                |
| Skills          | Optional later         | Useful for progressive disclosure of prompts or guidance       |
| Router          | Optional later         | Useful only for narrow classification problems                 |

## Planned Compile Shape

The target compile flow should look like this:

1. Normalize the request and parse all source documents.
2. Build a stable `document_order`.
3. For each document in order:
   1. Build a transient prompt context from durable workflow state plus the active document.
   2. Call the source analysis specialist.
   3. Update the durable compile context.
4. When the source-analysis phase completes, run synthesis.
5. Run review.
6. Retry synthesis when review fails and the limit has not been reached.
7. Escalate to human review on repeated failure.
8. Publish when approved.

## Durable State Versus Prompt Context

The compile context should be split into two layers.

### Durable workflow state

This is the checkpointed state that survives retries, restarts, and interrupts.

It should contain:

- current workflow fields that already matter for compile
- the accumulated multi-document context
- enough information to reconstruct bounded prompt context deterministically

### Transient per-pass prompt context

This is built for exactly one document-analysis call.

It should contain:

- the active document
- the most relevant prior context
- bounded guidance for consistent analysis

It should be discarded after the pass and rebuilt from durable state for the next pass.

## Proposed Future Typed Schema

The proposed future typed schema is captured in the planning document at [docs/plans/compile-multi-agent-supervisor-migration-plan.md](../plans/compile-multi-agent-supervisor-migration-plan.md).

That schema is design guidance only. It should not be treated as the current workflow schema.

## Runtime Boundary

The supervisor and its specialists should continue to resolve runtime capabilities through the shared app context.

That means:

- LLM providers still come from the configured plugin runtime
- storage still comes from the configured storage plugin
- configuration still comes from the merged WayGate settings model

This avoids hardcoding provider-specific assumptions into the planned agent layer.

## Migration Constraints

The target design must preserve these boundaries while orchestration evolves:

- `WorkflowTriggerMessage` remains the producer-to-worker contract
- thread id derivation remains stable
- `source_set_key` derivation remains stable
- publish outputs remain storage-backed and compatible with current consumers
- human-review resume semantics remain explicit and bounded
- raw, review, and published artifacts remain the durable system of record

## Decision Summary

The key design decisions are:

1. Keep LangGraph as the durable outer workflow.
2. Move compile control toward a supervisor-centered multi-agent model.
3. Replace large per-document fan-out with ordered document analysis.
4. Split compile context into durable workflow state and transient prompt context.
5. Treat the proposed typed schema as planning guidance until implementation begins.
