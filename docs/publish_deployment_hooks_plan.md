# Publish Deployment Hooks Plan

This document is the design anchor for Epic `#9` issue `#47`: add publish-triggered deployment hooks for site rebuilds.

## Purpose

WayGate's compiler already emits a clear publish boundary when a live document is written and an audit event is recorded. What it does not have is a decoupled mechanism for downstream presentation automation to react to those publish events. This plan defines a hook contract for site rebuild or deployment actions without moving presentation logic into the compiler node.

## Current Baseline

Implemented today:

- `publish_node()` writes the live markdown document to storage
- `publish_node()` records a `COMPILER_PUBLISH_COMPLETED` audit event
- middleware hooks already wrap compiler nodes for tracing and audit behavior
- there is no site build pipeline wired to publish events
- there is no deployment hook runner or event subscriber model

This means the repository already has a natural event boundary, but not a downstream automation contract.

## Non-Negotiable Constraints

1. Deployment logic must remain outside the core compiler publish node.
2. Hook failures must not invalidate successful content publication.
3. The hook contract must work with local preview and hosted deployment strategies.
4. The live markdown corpus remains the only source of truth for downstream builds.
5. The first design should reuse existing audit or event boundaries where possible.

## Recommended Trigger Boundary

The recommended trigger boundary is the successful completion of publish, not an earlier compiler step.

Candidate trigger source:

- the existing `COMPILER_PUBLISH_COMPLETED` audit event payload, or
- a lightweight publish-notification envelope emitted immediately after successful publish

The important point is that the compiler signals completion and then stops. It should not build or deploy the site inline.

## Recommended Hook Model

The first implementation-oriented direction should use an asynchronous hook consumer.

Recommended flow:

1. publish completes and writes the live document
2. a publish-completed event or artifact is emitted
3. a downstream hook runner decides whether a site rebuild is required
4. the hook runner triggers a site build or deployment task out of band
5. hook results are captured as audit or operational artifacts

This preserves compiler throughput and isolates presentation failures.

## Suggested Event Payload

A future publish-trigger envelope should likely include:

- `trace_id`
- `compiled_doc_id`
- `live_document_uri`
- `title`
- `document_type`
- `status`
- `visibility`
- publish timestamp
- optional affected tags

These fields are already close to what `publish_node()` knows today.

## Hook Decision Policy

Not every publish needs the same downstream action.

Recommended first decision rules:

- content publish -> trigger site rebuild eligibility check
- archived or deprecated content -> still eligible for rebuild because the site should reflect lifecycle changes
- local-only development mode -> allow no-op or preview-only behavior

The first phase should not attempt to optimize partial rebuild routing too early.

## Relationship To The Static-Site Pipeline

Issue `#45` defines how the site is built. This issue defines when that build should be triggered.

- `#45` owns the downstream site-build path
- `#47` owns the decoupled trigger mechanism
- the hook contract should stay generic enough that other downstream presentation tasks can subscribe later

## Suggested Design Roles

Recommended future roles:

- `PublishEventEmitter`: exposes a post-publish notification boundary
- `SiteRebuildScheduler`: decides whether and when to trigger a rebuild
- `DeploymentHookRunner`: executes local or remote rebuild actions
- `HookResultRecorder`: persists success or failure outcomes for operators

These are design roles, not current code.

## Failure Handling Model

Hook execution failures should be visible but non-blocking.

Recommended policy:

- publish success remains final even if rebuild triggering fails
- hook failures produce audit or maintenance-style operational records
- retries happen in the downstream automation layer, not through compiler re-runs

This separation is critical. A site deployment problem is not a document compilation failure.

## Local And Hosted Strategies

The contract should accommodate both:

- local preview rebuild commands for developer workflows
- hosted CI/CD or worker-based rebuild jobs for deployed environments

The event and hook model should therefore be transport-agnostic: queue job, CLI task, webhook, or CI dispatch are all valid future implementations.

## Interaction With Thematic Synthesis And Operator Views

- thematic synthesis outputs should use the same publish-trigger contract as ordinary live documents
- operator-facing metadata pages should also refresh through the same downstream site-build path
- the hook layer should not need special compiler branches for thematic or operator-focused content types

## Prototype Recommendation

For the first implementation-oriented prototype after this planning slice:

1. reuse `COMPILER_PUBLISH_COMPLETED` as the trigger source
2. add a separate hook consumer that can invoke a manual or local site-build task
3. record hook outcomes independently from compiler success
4. keep all deployment-target specifics outside the compiler package

This validates the separation of concerns before any hosted deployment system is chosen.

## Acceptance Mapping For Issue #47

- Defined publish-trigger mechanism: this document specifies the post-publish boundary and downstream hook flow.
- Decoupled from compiler path: the hook runner is explicitly outside `publish_node()`.
- Future site-publishing work can build from this: trigger payloads, roles, and failure policy are named directly.

## Explicitly Deferred

- implementing every deployment target
- embedding deployment logic inside compiler nodes
- advanced partial-rebuild optimization
- coupling hook failure to document publish failure
