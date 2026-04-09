# Static-Site Publishing Plan

This document is the design anchor for Epic `#9` issue `#45`: build a static-site publishing pipeline for the live wiki.

## Purpose

WayGate currently publishes compiled knowledge as markdown documents in storage. That is enough for agent-facing retrieval, but not for a browsable human-facing site. This plan defines a static-site publishing path that reads the existing live markdown corpus and renders it for human readers without changing the markdown source-of-truth model.

## Current Baseline

Implemented today:

- the compiler writes live markdown documents with canonical YAML frontmatter
- live documents carry status, visibility, lineage, sources, and provenance fields
- the retrieval SDK and MCP service consume the live markdown corpus directly
- there is no static-site generator configuration, site build output, or deployment workflow

Not implemented today:

- a human-facing site build pipeline
- metadata rendering rules for status, visibility, lineage, and provenance
- publish-triggered rebuild hooks
- a dedicated presentation-layer workspace or theme

## Non-Negotiable Constraints

1. Live markdown and frontmatter remain the source of truth.
2. The static site is a downstream build artifact, not a second authoring system.
3. Site generation stays separate from the core compiler logic.
4. The site must render existing metadata faithfully rather than inventing a parallel metadata contract.
5. The initial plan should prefer a markdown-native SSG over a custom application stack.

## Recommended Publishing Model

The recommended model is:

1. enumerate the live markdown corpus from storage or an exported workspace directory
2. normalize frontmatter into a site-ready content model
3. feed that content into a markdown-native static-site generator
4. emit a static build artifact for local preview or deployment

This keeps the presentation layer downstream of storage and compatible with future storage or deployment changes.

## Recommended SSG Direction

The first implementation-oriented direction should prefer a markdown-native generator such as MkDocs Material.

Why MkDocs is the stronger initial fit:

- markdown-first workflow aligns with the current live corpus
- low ceremony for turning document trees into browsable navigation
- straightforward metadata-aware templates and theme extension points
- simpler operational surface than building a custom frontend application

Docusaurus remains a viable later alternative, but it adds more framework surface than the current roadmap requires.

## Content Boundary

The static-site pipeline should consume only published live documents and selected metadata.

Recommended inputs:

- markdown body content
- `title`
- `doc_id`
- `document_type`
- `status`
- `visibility`
- `tags`
- `lineage`
- `sources`
- `source_hash`
- `last_compiled` and `last_updated`

The site pipeline should not need direct access to raw ingestion artifacts for the first phase.

## Navigation Model

Recommended first navigation layers:

- category navigation by `document_type`
- topical navigation by tags
- stable per-document pages keyed by slug and `doc_id`
- optional thematic landing pages once issue `#48` is implemented

This gives humans predictable browsing without requiring search or graph visualization on day one.

## Metadata Rendering Model

Recommended initial rendering rules:

- `status` as a visible lifecycle badge
- `visibility` as a caution or access-context badge
- `tags` as navigable chips or links
- `sources` as linked references
- `lineage` as a simple related-documents section before any richer visualization exists
- `last_compiled` as a freshness indicator

The operator-facing view model for richer lineage and provenance display belongs to issue `#46` and should refine this baseline later.

## Relationship To Thematic Synthesis

Thematic documents should be first-class site content once they exist.

- thematic overviews can become landing pages for broad topics
- contradiction summaries can surface disputed areas to human readers
- the site pipeline should not depend on thematic synthesis existing first, but it should leave room for those document types

## Build Boundary

The static-site build must stay outside the compiler publish node.

Recommended separation:

- compiler publishes live markdown
- site builder reads the live corpus and produces a static artifact
- deployment or rebuild triggers are handled later by issue `#47`

This avoids coupling document publication to presentation concerns.

## Suggested Design Roles

Recommended future roles:

- `LiveCorpusExporter`: prepares the live markdown corpus for the SSG input tree
- `SiteMetadataAdapter`: maps frontmatter into template-friendly page metadata
- `SiteBuilder`: runs the chosen SSG and emits the site artifact
- `SiteThemeAdapter`: controls badges, provenance sections, and navigation templates

These are design roles, not current code.

## Local Preview Model

The first implementation-oriented prototype should support a local build-preview loop.

Recommended developer flow:

- export or mount the live corpus into a docs/site input tree
- run the SSG locally
- inspect generated pages without touching the compiler runtime

This keeps early presentation work easy to iterate on before any deployment automation exists.

## Operational Considerations

- build failures should not block the core compiler pipeline
- the site artifact should be reproducible from the same live corpus state
- static builds should tolerate missing optional metadata gracefully
- future deployment hooks should trigger rebuilds asynchronously rather than inline with publish

## Prototype Recommendation

For the first implementation-oriented prototype after this planning slice:

1. choose one markdown-native SSG, preferably MkDocs Material
2. export a minimal live-corpus input tree
3. render per-document pages with status, visibility, tags, lineage, and sources
4. keep rebuilds manual until issue `#47` defines the publish-trigger contract

This validates the human-facing publishing path without turning the presentation layer into a product rewrite.

## Acceptance Mapping For Issue #45

- Defined static-site path: this document specifies the downstream site-build model.
- Human-facing browsing from live markdown: the proposed pipeline turns the live corpus into a browsable site without replacing markdown as the source of truth.
- Separation from compiler responsibilities: build and deployment remain outside the publish node.

## Explicitly Deferred

- a full custom frontend application
- replacing markdown as the source of truth
- publish-triggered rebuild automation
- general-purpose analytics or operator dashboards
