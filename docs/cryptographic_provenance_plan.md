# Cryptographic Provenance Plan

This document is the design anchor for Epic `#8` issue `#43`: evaluate cryptographic provenance extensions for compiled knowledge.

## Purpose

WayGate already records useful provenance in raw and live metadata, but it does not yet provide cryptographic guarantees about who attested to a compiled document or whether a published artifact was modified after compilation. This document evaluates what stronger provenance would protect, what prerequisites are missing today, and why this work should remain design-only for now.

## Current Provenance Baseline

Implemented today:

- Raw documents can carry `doc_id`, `source_url`, `source_hash`, `visibility`, tags, and source-specific metadata.
- Compiled live documents receive a deterministic `doc_id` based on title and lineage.
- Publish promotes `lineage`, `sources`, tags, and an aggregated `source_hash` into live frontmatter.
- `build_provenance_hash()` combines raw source hashes or fallback raw `doc_id` values into one aggregate digest.
- Audit and maintenance artifacts provide operational history for enqueue, compilation, publish, recompilation, and archival flows.

What this gives the system today:

- change detection when source material changes
- document ancestry tracking through `lineage`
- basic provenance reconstruction from source URIs and stored raw metadata

What it does not give the system today:

- proof of who attested to a compiled output
- tamper-evident signatures over published content
- verifiable fact-level binding between claims and sources
- key rotation, revocation, or trust policy

## Non-Negotiable Constraints

1. Markdown and frontmatter remain the durable source of truth.
2. Any cryptographic provenance layer must complement, not replace, current metadata and audit artifacts.
3. The first step is evaluation only, not signing infrastructure rollout.
4. Verification must be automatable and understandable by maintainers.
5. The design must preserve the current ingest -> compile -> publish split.

## What Stronger Cryptographic Provenance Would Protect

Potential protections include:

- proving a specific compiler run produced a specific published artifact
- proving a published artifact was derived from a particular raw-source set
- detecting post-publish tampering of frontmatter or document body
- attaching signer identity to a publish event or maintenance attestation
- enabling offline verification without trusting the running service blindly

This is materially stronger than the current `source_hash` plus `lineage` model, which is valuable for integrity checks but not an authenticated receipt chain.

## Why Current Provenance Is Not Enough

The current model records relationships, but it does not cryptographically bind them to an attester.

Gaps in the current baseline:

- `source_hash` is an aggregate digest, not a signed receipt.
- `lineage` shows ancestry, but not whether the ancestry claim was authenticated.
- published markdown can be modified after generation without invalidating a stored signature, because no signature exists.
- audit events are durable records, but not trust anchors.

In short, the current system supports explainability and maintenance, but not strong non-repudiation.

## Receipt Model Options

### Option 1: Document-level signed publish receipts

- Sign the canonical published artifact digest at publish time.
- Bind the receipt to the compiled document id, source hash, lineage, timestamp, and signer identity.

Benefits:

- simplest model to reason about
- aligns directly with the current publish step
- easiest first verification story

Tradeoffs:

- protects the whole document, not individual claims
- any content edit requires a new receipt

### Option 2: Source-set attestation receipts

- Sign the normalized set of raw document identities and hashes that fed a compile.
- Optionally store the publish digest separately.

Benefits:

- emphasizes derivation from source material
- can survive some presentation-layer changes if the source set stays constant

Tradeoffs:

- weaker linkage to the exact compiled body unless combined with a publish digest
- still does not prove fact-level grounding

### Option 3: Fact-level receipts

- Sign individual claims or extracted facts and their source bindings.

Benefits:

- strongest precision for high-assurance environments
- best support for partial verification and downstream evidence views

Tradeoffs:

- far more complex claim extraction and canonicalization problem
- not viable before the repository has a stable fact model

## Recommended Evaluation Direction

If this work ever moves beyond planning, the first viable step should be document-level signed publish receipts.

Reasoning:

- it fits the current publish node naturally
- it avoids premature fact-extraction design
- it provides immediate tamper evidence for the compiled artifact

## Suggested Receipt Contents

A future document-level receipt would likely need to bind at least:

- `compiled_doc_id`
- canonical published content digest
- canonical frontmatter digest
- `lineage`
- normalized `sources`
- aggregated source-set digest
- compile timestamp
- signer key identifier
- receipt version

These are evaluation targets, not new current fields.

## Canonicalization Prerequisites

Cryptographic signing only works if the signed payload is canonical.

Minimum prerequisites before implementation:

- stable serialization rules for frontmatter field ordering
- stable newline and whitespace normalization for published markdown
- stable ordering for lineage and source lists before hashing
- explicit receipt versioning

Without canonicalization, verifiers will disagree about what was signed.

## Storage And Verification Prerequisites

Before any implementation, WayGate would need:

- a receipt storage location or embedding rule
- a verification command or maintenance workflow
- signer identity and key-distribution rules
- key rotation and revocation strategy
- failure policy for missing or invalid receipts

This is why the issue remains evaluation-only.

## Where Receipts Could Live

Possible future storage options:

- embedded in live frontmatter
- stored as sidecar artifacts under `meta/`
- persisted as audit-linked publish receipts with references from the live document

The best fit is likely a sidecar or audit-linked artifact so the main frontmatter contract stays compact.

## Relationship To Current Audit And Maintenance Artifacts

Cryptographic receipts should build on the current audit and maintenance model, not replace it.

- audit events still explain operational flow
- maintenance findings still track stale or invalid knowledge states
- receipts would add attested integrity, not orchestration logic

This separation keeps the system understandable: operational history remains one concern, trust verification another.

## Key Management And Trust Questions

This roadmap item cannot become implementation work until several policy questions are answered:

- who is the signer: service identity, operator, or release pipeline
- where keys are stored
- whether signatures are online, offline, or CI-generated
- who is allowed to verify and trust them
- what happens when a key is compromised or rotated

These policy questions are a major reason to keep the current issue at evaluation scope.

## Interaction With Consensus And Missing Context

- Structured consensus may later provide better evidence about uncertainty, but it is not a substitute for signed provenance.
- Missing-context handling may change the source set for a document, which means any receipt model must tolerate recompilation and supersession.
- Receipt chains must therefore expect new signed generations rather than one permanent signature per topic.

## Prototype Recommendation

For the first implementation-oriented prototype after this planning slice:

1. Define a canonical document digest format.
2. Emit an unsigned receipt envelope first.
3. Verify that recompilation and publish updates can invalidate and replace prior envelopes cleanly.
4. Only then evaluate signing with a concrete key-management model.

This reduces the risk of committing to signatures before the payload and lifecycle semantics are stable.

## Acceptance Mapping For Issue #43

- Documented evaluation: this document defines the options, protections, and tradeoffs.
- Explicit prerequisites: canonicalization, storage, verification, and key-management requirements are named directly.
- Clear follow-on work: future implementation can start from document-level receipt evaluation rather than reopening the whole problem.

## Explicitly Deferred

- Production signing infrastructure.
- Full regulatory or legal compliance programs.
- Fact-level receipt implementation.
- Immediate schema expansion in current metadata models.
