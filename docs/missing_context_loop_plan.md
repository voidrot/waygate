# Missing Context Loop Plan

This document is the design anchor for Epic `#8` issue `#42`: design the missing-context research loop for briefing gaps.

## Purpose

WayGate already lets callers persist durable context-gap reports through the MCP boundary, and maintenance can already replay recompilation work from those persisted findings. This plan defines how a future missing-context loop should extend that substrate into a fuller research-and-ingestion cycle without introducing a second gap-report channel.

## Current Implemented Substrate

The repository already ships the core pieces needed for a later missing-context loop:

- `generate_briefing` and `preview_retrieval` run through the MCP service boundary.
- `report_context_error` persists a durable `ContextErrorReport` through `record_context_error()`.
- `record_context_error()` writes a `MaintenanceFinding` of type `context_error`.
- When lineage anchors are present, the persisted finding embeds a `RecompilationSignal`.
- Compiler maintenance can load persisted context-error findings and replay recompilation jobs.
- Receiver and compiler are already decoupled by the queue and storage boundary.

This means the missing-context roadmap should start from durable artifacts that already exist rather than inventing a new transient callback or side channel.

## Non-Negotiable Constraints

1. `report_context_error` remains the canonical entrypoint for explicit context-gap reporting.
2. Missing-context automation must preserve the current receiver -> storage -> compiler split.
3. Newly gathered information must return through normal ingestion paths.
4. Research automation must not bypass visibility rules or provenance tracking.
5. The system must degrade gracefully when follow-up research is unavailable.

## What Counts As A Context Gap

Recommended categories for future handling:

- `missing_source_detail`: the current lineage anchors point to relevant documents, but they lack the specific fact needed.
- `missing_neighbor_context`: the answer likely exists in nearby lineage or backlink neighborhoods that were not traversed.
- `missing_external_context`: the repository does not appear to contain the needed source material.
- `stale_context`: the live document set is present but likely outdated relative to known source changes.

The first future implementation should remain conservative and rely on explicit caller reports plus simple heuristics rather than attempting to infer every gap autonomously.

## Recommended Loop

The missing-context loop should operate in five stages.

1. A caller generates a briefing or retrieval preview and determines the result is insufficient.
2. The caller persists a `ContextErrorReport` through `report_context_error`.
3. A maintenance or orchestration worker classifies the persisted finding.
4. The worker chooses one of two actions:
   - replay recompilation from existing lineage when the corpus likely contains enough information already
   - dispatch research ingestion when the corpus is genuinely missing source material
5. Any newly gathered raw material is written through standard ingestion plugins, then compiled through the normal queue-driven compiler path.

## Dispatch Model

Recommended future dispatch roles:

- `ContextGapClassifier`: inspects a persisted context-error finding and assigns a gap category.
- `RecompilationDecider`: determines whether existing lineage or graph expansion is enough to retry compilation.
- `ResearchDispatcher`: creates follow-up ingestion work when new source collection is required.
- `ResearchResultNormalizer`: converts follow-up research into canonical `RawDocument` records.

These are design roles, not current code.

## Why The Existing Artifact Path Should Be Reused

The existing context-error artifact already has the right operational properties:

- durable storage
- trace correlation
- optional lineage anchors
- visibility context
- compatibility with maintenance sweeps

Creating a second missing-context channel would split observability, duplicate orchestration logic, and make replay behavior harder to reason about.

## Relationship To Retrieval And Graph Expansion

The missing-context loop depends on the retrieval and graph roadmap defined in issues `#44` and `#41`.

- Some context gaps will stop being gaps once hybrid retrieval or graph expansion exists.
- The classifier should distinguish between a retrieval miss and a true source-coverage gap.
- Graph traversal should be attempted before dispatching external research when the current corpus likely contains adjacent evidence.

The adjacent compiler-side consensus roadmap is documented in
`docs/structured_consensus_plan.md` so disagreement can be separated from true
knowledge gaps.

## Receiver And Compiler Integration

Future research results should re-enter the system through the same ingest-to-compile contract used today.

- External or automated research produces source payloads.
- A receiver-side adapter normalizes those payloads into canonical `RawDocument` records.
- Raw documents are written to storage.
- The existing queue enqueues compiler work with normal trace and audit events.
- Publish promotes the new provenance into live frontmatter.

This preserves the current operational boundaries and keeps provenance accumulation consistent.

## Recommended Artifact Shape For Future Classification

Future classification can extend the persisted maintenance finding payload rather than changing the top-level schema immediately.

Suggested payload additions:

- `gap_category`
- `dispatch_action`
- `research_topic`
- `suggested_sources`
- `retrieval_trace`

This keeps the durable maintenance envelope stable while allowing richer orchestration metadata later.

## Safety And Governance Rules

- Follow-up research must not expand caller visibility beyond the effective retrieval scope.
- Research-generated raw inputs must preserve source attribution and hashes when available.
- Failed research dispatches should remain inspectable as durable artifacts rather than disappearing into logs.
- Automatic external lookup should remain opt-in and policy-controlled.

## Operational Model

The missing-context loop should be asynchronous.

- Briefing generation stays fast and synchronous.
- Gap reporting is synchronous only long enough to persist the durable artifact.
- Classification, research dispatch, and ingestion happen out of band.
- Maintenance commands or future workers may batch and replay unresolved findings.

## Prototype Recommendation

For the first implementation-oriented prototype after this planning slice:

1. Add a classifier that reads persisted `context_error` findings.
2. Distinguish only two actions at first: `recompile_existing` and `research_missing`.
3. Reuse the embedded `RecompilationSignal` path for `recompile_existing`.
4. Represent `research_missing` as a durable queued task specification without shipping the actual research agent.

This would validate the feedback-loop contract without forcing premature web-search or agent rollout.

## Acceptance Mapping For Issue #42

- Concrete missing-context design: this document defines the gap categories, dispatch model, and ingest-to-compile feedback loop.
- Compatible with existing architecture: it reuses the current MCP, maintenance, receiver, and compiler boundaries.
- Clear follow-on contract: later implementation can build on the classifier, dispatcher, and durable artifact recommendations.

## Explicitly Deferred

- Building the full research agent.
- Web-search integration.
- Autonomous gap detection from every retrieval call.
- Immediate graph-powered retrieval implementation.
