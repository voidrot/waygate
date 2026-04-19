# Compile Multi-Agent Supervisor Migration Plan

## Purpose

This document preserves the migration plan for the compile workflow while also
recording the implementation status of the `compile-supervisor-sequential`
worktree.

This remains a planning and status document, not the source of truth for
current runtime behavior. For current behavior in this branch, use:

- `docs/design/ingestion-and-workflows.md`
- `docs/design/compile-supervisor-multi-agent.md`

## Current Status

The main compile migration goals are implemented in this branch.

Completed:

- LangGraph remains the durable outer workflow layer.
- Compile source analysis is sequential rather than broad fan-out.
- Source analysis now runs under a supervisor with specialist subagents.
- Durable state and transient prompt context are explicitly separated.
- Prompt context reconstruction is relevance-based and bounded.
- Cross-document continuity state is accumulated and can be resolved by later
  documents.
- Optional storage-backed prompt guidance is supported through the `agents`
  namespace.

Still pending outside the scope of this branch-local plan closeout:

- live end-to-end compile validation with a real provider stack
- any further decomposition of source-analysis specialists

## Original Goals

The migration set out to:

1. move compile orchestration toward a supervisor-centered multi-agent design
2. preserve LangGraph as the durable workflow layer
3. replace broad fan-out with sequential document analysis
4. keep raw, review, and published artifacts as the durable system of record
5. preserve workflow trigger and publish result contracts during migration

Those goals are now reflected in the branch implementation.

## Stage Summary

### Stage 1

Document the target architecture and current-versus-planned boundaries.

Status: completed in this branch through the branch-local design docs.

### Stage 2

Extract current compile responsibilities into explicit supervisor-era roles.

Status: completed through the compile agent layout and thin node wrappers.

### Stage 3

Wrap specialist logic behind supervisor-controlled tools or subagents.

Status: completed for source analysis through the document-analysis supervisor.

### Stage 4

Replace fan-out with sequential analysis and durable context updates.

Status: completed in this branch.

### Stage 5

Consider optional skills or router usage for non-core cases.

Status: partially completed through optional storage-backed guidance in the
`agents` namespace. Router-based compile control remains intentionally out of
scope.

## Remaining Follow-Up

The remaining work is no longer migration mechanics. It is validation and
branch integration:

- run a real compile against the configured provider stack
- reconcile branch-local docs with the main repository docs before merge
- decide whether to split continuity into narrower internal specialists later
