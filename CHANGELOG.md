# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning principles for release notes.

## [Unreleased]

### Added

- Root monorepo pytest bootstrap with shared discovery and coverage gate.
- Canonical schema tests for `RawDocument`, `FrontMatterDocument`, and source metadata contract behavior.
- Source metadata contract baseline with required `kind` and provider-specific metadata models.
- Storage metadata query API: `get_raw_document_metadata(doc_id)`.
- Local storage metadata round-trip support using `python-frontmatter` plus comprehensive provider tests.
- Compiler helper and publish-node tests validating source-context rendering and frontmatter promotion correctness.
- GitHub and Slack receiver plugins with webhook parsing behavior tests.
- Generic webhook metadata model and metadata-focused receiver tests.
- Reusable markdown template helpers in `libs/core/src/waygate_core/file_templates.py` with draft-node coverage.
- This changelog file for ongoing release tracking.

### Changed

- `RawDocument` and `FrontMatterDocument` now carry canonical provenance fields (`doc_id`, `source_url`, `source_hash`, `visibility`, `tags`, `lineage`, `sources`, `source_metadata`).
- `FrontMatterDocument` now includes `document_type`, and frontmatter generation serializes both raw and live canonical fields through shared helper paths.
- Compiler graph state now carries raw metadata through Draft -> Review -> Publish.
- Draft prompt now includes structured source context plus a reusable markdown template scaffold.
- Publish node now promotes lineage/sources/tags from raw metadata into live frontmatter, derives deterministic compiled document IDs, and writes collision-resistant live filenames.
- Receiver trigger now forwards structured raw metadata to the compiler queue state and seeds a derived topic instead of the `Auto-Detect` placeholder.
- Local storage now organizes raw documents by source type and supports managed `meta/templates` and `meta/agents` locations.
- Webhook receivers now emit canonical metadata defaults and typed source metadata placeholders.

### Documentation

- Updated README and docs to reflect implemented metadata contract and current architecture boundaries.
- Added explicit out-of-scope notes for retrieval-time RBAC filtering engine and advanced provenance engines.

### Fixed

- Backward compatibility for legacy raw frontmatter lacking `source_metadata.kind` (graceful metadata fallback).
- Suppressed known third-party Python 3.14 warning noise in test runs for stable local verification output.
