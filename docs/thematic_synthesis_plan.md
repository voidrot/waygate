# Thematic Synthesis Plan

This document is the design anchor for Epic `#9` issue `#48`: add a thematic synthesis worker for roll-up and contradiction-summary documents.

## Purpose

WayGate currently compiles documents from newly ingested raw inputs into individual live markdown pages. It does not yet generate macro-level overview documents that summarize clusters of related pages or call out contradictions across them. This plan defines a separate thematic-synthesis workstream that builds on the live corpus without changing the current per-ingest compiler path.

## Current Baseline

Implemented today:

- The receiver writes canonical raw documents and enqueues compile jobs.
- The compiler runs a per-ingest Draft -> Review -> Publish graph.
- Publish writes one live document for the current compile topic.
- Retrieval operates over the live markdown corpus and can already filter by tags, document type, status, and lineage.

Not implemented today:

- a worker that scans the live corpus for topic clusters
- thematic roll-up documents generated independently of new ingestion events
- contradiction-summary documents across related live pages
- any special retrieval preference for thematic overview content

## Non-Negotiable Constraints

1. The thematic worker is downstream of the live markdown corpus, not a replacement for per-source compilation.
2. Live markdown and frontmatter remain the source of truth.
3. Thematic synthesis must stay separate from the core per-ingest Draft -> Review -> Publish path.
4. Generated roll-ups must preserve provenance back to the contributing live documents.
5. Contradiction summaries must flag disagreement explicitly rather than silently collapsing conflicting claims.

## Worker Boundary

The thematic worker should be a separate compilation mode or adjacent worker, not an extra branch inside the current ingest-triggered graph.

Recommended split:

- per-ingest compiler path: turns raw inputs into granular live documents
- thematic synthesis worker: reads existing live documents and produces macro-level summaries

This keeps ingestion latency and failure handling separate from higher-level synthesis.

## Cluster Selection Model

Recommended first cluster-selection inputs:

- shared tags
- overlapping lineage anchors
- document type groupings
- explicit curated seed lists for high-value overview topics

The first implementation-oriented prototype should stay conservative and begin with deterministic tag-based clustering.

## Output Contract

Recommended thematic output types:

- `thematic_overview`: a broad summary of a coherent cluster of live documents
- `contradiction_summary`: a focused document that highlights disagreement or unresolved tension across a cluster

Recommended output properties:

- stable title and doc id
- explicit list of contributing live document ids or URIs
- aggregated tags
- clear status and visibility
- source list that points to contributing live documents rather than raw ingestion sources only
- body sections that distinguish stable conclusions from open contradictions

## Provenance Model

Thematic documents should derive their provenance from live-document inputs.

- `lineage` should reference the contributing live document ids used for synthesis
- `sources` should include contributing live document URIs and optionally preserved upstream sources when useful
- `source_hash` should be derived from the contributing live document state

This keeps thematic pages explainable without pretending they came directly from one raw source.

## Contradiction Handling

Contradiction detection should be explicit and bounded.

Recommended first behavior:

- identify conflicting statements across the selected document set
- summarize the disagreement in a dedicated section
- avoid forcing false resolution when the source material remains ambiguous

The first prototype should focus on contradiction surfacing, not automatic contradiction resolution.

## Relationship To Retrieval

The thematic worker exists partly to reduce retrieval pressure for broad questions.

- broad queries can later prefer `thematic_overview` documents when available
- contradiction summaries can become high-value context for topics with unstable or disputed knowledge
- the retrieval contract itself should remain unchanged; preference logic can be layered later

## Suggested Execution Model

Recommended trigger patterns for later implementation:

- scheduled synthesis passes over selected tags or topics
- manual operator-triggered refresh for curated overview topics
- maintenance-triggered refresh when many underlying cluster documents change

The first prototype should avoid publish-triggered synchronous synthesis to keep the core compiler path simple.

## Suggested Design Roles

Recommended future roles:

- `ClusterSelector`: identifies candidate live-document sets
- `ThemeSynthesizer`: drafts overview or contradiction-summary content
- `ThemeReviewer`: validates grounding against the contributing live documents
- `ThemePublisher`: writes thematic documents into the live corpus with explicit provenance

These are design roles, not current code.

## Recommended Storage Shape

The simplest future target is to publish thematic outputs into the existing live corpus under the existing document model.

- keep markdown and frontmatter format unchanged
- use `document_type: thematic`
- distinguish overview vs contradiction summary inside metadata or title conventions

This avoids inventing a second presentation store before the static-site work is defined.

## Operational Considerations

- thematic synthesis should be resumable and independently observable
- failures should not block per-ingest compilation
- audit events should identify cluster inputs and output document ids
- maintenance can later invalidate or refresh thematic documents when contributing pages become stale

## Prototype Recommendation

For the first implementation-oriented prototype after this planning slice:

1. Add a deterministic tag-based cluster selector.
2. Support only one output mode: `thematic_overview`.
3. Keep synthesis execution manual or scheduled, not publish-triggered.
4. Write outputs as normal live markdown using existing frontmatter fields.

This is enough to validate the worker boundary and retrieval value without coupling it to static-site or deployment concerns.

## Acceptance Mapping For Issue #48

- Defined workstream: this document defines the thematic-synthesis worker boundary and scope.
- Separate from per-source compilation: the worker reads the live corpus and remains outside the per-ingest compiler path.
- Future implementation anchor: clustering, output contract, contradiction handling, and execution roles are named directly.

## Explicitly Deferred

- full hybrid retrieval behavior
- static-site rendering
- publish-triggered deployment hooks
- automatic contradiction resolution
