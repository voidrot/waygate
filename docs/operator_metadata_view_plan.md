# Operator Metadata View Plan

This document is the design anchor for Epic `#9` issue `#46`: design human-facing lineage and provenance views for operators.

## Purpose

WayGate already stores rich metadata in live markdown frontmatter, but there is no defined human-facing view model for operators who need to inspect freshness, provenance, lineage, visibility, and source references. This plan defines that presentation contract so future static-site or other operator-facing tools can render the current metadata model consistently.

## Current Metadata Surface

The repository already publishes the key fields operators need:

- `doc_id`
- `title`
- `document_type`
- `source_type`
- `source_url`
- `source_hash`
- `status`
- `visibility`
- `tags`
- `last_compiled`
- `last_updated`
- `lineage`
- `sources`
- `source_metadata`

These fields are enough to define a first operator-facing view model without changing the storage schema.

## Non-Negotiable Constraints

1. The operator view must reflect the existing metadata contract rather than inventing a parallel one.
2. Live markdown and frontmatter remain the source of truth.
3. Operator presentation must work in a static-site context first, but not be tied exclusively to one renderer.
4. Visibility semantics must remain informative and cautious, not access-controlling by themselves.
5. The first design should prefer simple, explainable representations over interactive complexity.

## Operator Questions The View Must Answer

The operator-facing model should let a human answer these questions quickly:

- What is this document and what kind of page is it?
- How fresh is it?
- What source material fed it?
- What other documents does it derive from?
- Is it live, archived, or otherwise degraded?
- Does the visibility label suggest handling constraints?

## Recommended Page Sections

Recommended baseline layout for any human-facing document page:

1. identity header
2. lifecycle and freshness summary
3. provenance and source references
4. lineage and related-documents summary
5. tags and thematic context
6. main document body

This makes metadata inspectable without overwhelming the reader before the actual content.

## Identity Header

Recommended elements:

- `title`
- `document_type`
- `doc_id`
- `source_type`

This section should answer what the page is in one scan.

## Lifecycle And Freshness Section

Recommended rendering rules:

- `status` as a prominent lifecycle badge
- `last_compiled` as the primary freshness timestamp
- `last_updated` as a secondary compatibility field when present

Suggested operator cues:

- `live` or `active` -> normal state
- `stale_warning` -> caution banner
- `archived` -> de-emphasized content plus an archival warning

## Provenance And Source Section

Recommended rendering rules:

- `sources` as the main linked source reference list
- `source_url` as the canonical single-source reference when present
- `source_hash` as an integrity detail in an expandable metadata section
- `source_metadata` as structured supplementary context when available

This section should prioritize human legibility first and raw integrity fields second.

## Lineage Section

Recommended first-phase rendering:

- render `lineage` as a related-documents list
- show each lineage entry as a linked document reference when resolvable
- explain lineage as ancestry or upstream derivation rather than as a generic graph term

The first phase should avoid interactive graph visualizations until the underlying view model is stable.

## Visibility Presentation Rules

Visibility should be presented as context, not false enforcement.

Recommended cues:

- `public` -> neutral badge
- `internal` -> caution badge
- `strictly_confidential` -> strong warning badge

The UI should never imply that a badge alone enforces access control. Enforcement remains elsewhere.

## Tag And Thematic Context Section

Recommended rendering:

- `tags` as clickable filters or chips where the presentation layer supports navigation
- `document_type: thematic` should be visually distinguished from granular source-derived pages
- future contradiction-summary pages should be clearly marked as synthesis artifacts rather than raw-source mirrors

## Progressive Disclosure Model

Operators need both fast scanning and deeper inspection.

Recommended split:

- default-visible summary badges and lists for freshness, status, visibility, tags, and source links
- expandable details for `doc_id`, `source_hash`, raw lineage ids, and source-specific metadata blocks

This keeps ordinary browsing readable while preserving audit-friendly detail.

## Relationship To Static-Site Publishing

This document defines the presentation contract that the static-site publishing layer should render.

- the site pipeline from issue `#45` provides the build path
- this issue defines what metadata the site should show and how it should be framed for humans
- richer operator navigation can evolve later without changing the core metadata model

The downstream publish-trigger contract that should refresh those rendered pages
is documented in `docs/publish_deployment_hooks_plan.md`.

## Relationship To Thematic Synthesis

Thematic overviews and contradiction summaries should follow the same operator-view contract, with a few additions:

- clearly mark them as synthesized roll-up documents
- list contributing documents in the provenance section
- highlight disagreement summaries explicitly when contradiction content exists

## Suggested View-Model Roles

Recommended future roles:

- `OperatorPageModel`: normalized page metadata for rendering
- `LineageReferenceResolver`: resolves lineage ids into human-readable document references
- `ProvenanceSectionBuilder`: formats sources, hashes, and source metadata for presentation
- `StatusBadgePolicy`: maps lifecycle and visibility fields into display treatments

These are design roles, not current code.

## Prototype Recommendation

For the first implementation-oriented prototype after this planning slice:

1. define a normalized operator page model from `FrontMatterDocument`
2. render lineage as a simple linked list, not an interactive graph
3. render `source_hash` and `doc_id` in expandable detail sections
4. keep all richer graph or analytics views deferred

This validates the human-facing metadata contract before UI complexity grows.

## Acceptance Mapping For Issue #46

- Documented operator-facing view model: this document defines the key sections and rendering rules.
- Explicit lineage and provenance display requirements: lineage, sources, status, visibility, hashes, and freshness are all covered.
- Future presentation implementation anchor: the static-site pipeline or any later UI can reference this contract directly.

## Explicitly Deferred

- full UI implementation
- general-purpose analytics dashboards
- interactive graph visualization as the default lineage view
- replacing the current metadata contract
