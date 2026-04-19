# Compile Multi-Agent Supervisor Migration Plan

## Purpose

This document captures the proposed migration from the current single-graph compile workflow to a supervisor-centered multi-agent workflow.

This is a planning document, not the source of truth for current behavior. For the currently implemented workflow contract, use:

- [docs/design/ingestion-and-workflows.md](../design/ingestion-and-workflows.md)
- [docs/design/architecture.md](../design/architecture.md)
- [docs/design/data-models-and-storage.md](../design/data-models-and-storage.md)

## Status

Historical migration plan with active follow-up guidance. The core mechanics described here are now implemented in `libs/workflows`, including sequential document analysis, supervisor-controlled source analysis, a durable-versus-transient context split, cross-document continuity carryforward, and optional storage-backed guidance loading.

Remaining follow-up work is narrower:

- run a real end-to-end compile against a configured provider stack
- decide whether source analysis should split continuity into narrower specialist roles
- keep the current design docs aligned with the runtime implementation as the workflow evolves

## Goals

The migration should achieve these goals:

1. Move compile orchestration toward a supervisor-centered multi-agent design.
2. Preserve LangGraph as the durable outer workflow layer for persistence, retries, and interrupts.
3. Replace broad per-document fan-out with sequential document analysis so later passes can build on earlier discoveries.
4. Keep raw artifacts, review artifacts, and published markdown as durable system-of-record outputs.
5. Preserve current external contracts for workflow trigger handling and publish result shapes during migration.

## Core Decision

The target compile architecture should use LangGraph custom workflow plus a LangChain supervisor with specialist subagents.

The key design choice is not only the supervisor pattern. It is the combination of:

- durable orchestration in LangGraph
- centralized routing in the supervisor
- sequential source-document analysis
- bounded transient prompt context per document pass

This explicitly rejects keeping the current blind fan-out as the long-term compile model.

## Pattern Selection

| Pattern         | Role in WayGate compile                                                       |
| --------------- | ----------------------------------------------------------------------------- |
| Subagents       | Primary pattern for specialist compile work coordinated by a supervisor       |
| Custom workflow | Required outer orchestration layer for checkpointing, retries, and interrupts |
| Handoffs        | Secondary pattern for human review or operator-controlled remediation         |
| Skills          | Optional later mechanism for loading prompt packs or specialized guidance     |
| Router          | Optional later helper for narrow workflow-type or source-type classification  |

## Why Sequential Analysis Wins Here

The compile workflow should process multiple raw documents in a stable order rather than in a large fan-out.

That ordering allows each new analysis pass to inherit prior discoveries, including:

- canonical topics
- canonical tags
- glossary terms
- entity naming
- claims already grounded in prior documents
- references to earlier documents that should be recognized rather than rediscovered

This reduces drift between summaries and makes downstream synthesis more consistent.

## Target Architecture

### Outer orchestration

LangGraph remains responsible for:

- initial request normalization
- persistent workflow state
- sequential loop control over document analysis
- synthesis and review loop boundaries
- human-review interrupts and resume
- publish side effects

### Inner orchestration

The supervisor agent is responsible for:

- choosing the next specialist action
- enforcing stable document ordering
- assembling bounded prompt context for the active document
- updating the accumulated compile context after each document pass
- deciding when the source-analysis phase is complete enough to synthesize

### Specialist roles

Recommended baseline roles:

1. Source normalization specialist
2. Source analysis specialist
3. Synthesis specialist
4. Review specialist
5. Publish specialist
6. Human-review specialist

The source analysis specialist is the key migration target. It should be called once per document in sequence, not over a wide parallel fan-out.

## Workflow Shape

The planned target flow is:

1. Normalize request and parse source documents.
2. Build `document_order` from the parsed source set.
3. For each source document in order:
   1. Build a bounded transient prompt context from durable workflow state and the active document.
   2. Run source analysis.
   3. Update the durable compile context.
4. Run synthesis.
5. Run review.
6. If review fails and the revision limit is not reached, return to synthesis.
7. If review fails and the revision limit is reached, enter human review.
8. Publish on approval or human override.

## Durable Versus Transient State

The future compile context should be split into two layers.

### Persistent durable workflow state

This layer is checkpointed and resumable. It must remain JSON-serializable and safe for LangGraph persistence.

It should preserve current fields such as:

- `source_documents`
- `source_set_key`
- `extracted_metadata`
- `document_summaries`
- `scratchpad`
- `current_draft`
- `review_feedback`
- `revision_count`
- `human_review_action`
- `published_document_uri`
- `published_document_id`

It should be expanded with the future accumulated compile context described below.

### Transient per-pass prompt context

This layer is built fresh for one document-analysis call and then discarded.

It should contain only:

- the active document
- bounded relevant subsets derived from durable state
- prompt instructions for the current pass

It should never become a second long-term source of truth.

## Proposed Future Typed Schema

The following schema is design guidance only. It is not implemented yet and should not be treated as the current runtime schema.

```python
from __future__ import annotations

from typing import Literal
from typing_extensions import TypedDict


class OrderedDocumentRef(TypedDict):
    uri: str
    source_hash: str | None
    source_uri: str | None
    source_type: str | None
    timestamp: str | None


class ProcessedDocumentBrief(TypedDict):
    uri: str
    summary: str
    key_claims: list[str]
    defined_terms: list[str]
    discovered_topics: list[str]
    discovered_tags: list[str]
    referenced_entities: list[str]
    supporting_source_uris: list[str]


class CanonicalTopicEntry(TypedDict):
    name: str
    aliases: list[str]
    supporting_source_uris: list[str]


class CanonicalTagEntry(TypedDict):
    name: str
    aliases: list[str]
    supporting_source_uris: list[str]


class GlossaryEntry(TypedDict):
    term: str
    aliases: list[str]
    definition_hint: str | None
    supporting_source_uris: list[str]


class EntityRegistryEntry(TypedDict):
    kind: Literal["person", "organization", "project"]
    canonical_name: str
    aliases: list[str]
    supporting_source_uris: list[str]


class ClaimLedgerEntry(TypedDict):
    claim_id: str
    text: str
    supporting_source_uris: list[str]
    related_entities: list[str]
    related_terms: list[str]


class ReferenceIndexEntry(TypedDict):
    key: str
    kind: Literal["term", "entity", "claim"]
    source_uris: list[str]
    processed_document_uris: list[str]
    claim_ids: list[str]


class UnresolvedMentionEntry(TypedDict):
    raw_text: str
    kind_hint: str | None
    source_uri: str
    status: Literal["open", "resolved", "dropped"]


class CompileDurableState(TypedDict):
    document_order: list[OrderedDocumentRef]
    document_cursor: int
    prior_document_briefs: list[ProcessedDocumentBrief]
    canonical_topics: list[CanonicalTopicEntry]
    canonical_tags: list[CanonicalTagEntry]
    glossary: list[GlossaryEntry]
    entity_registry: list[EntityRegistryEntry]
    claim_ledger: list[ClaimLedgerEntry]
    reference_index: list[ReferenceIndexEntry]
    unresolved_mentions: list[UnresolvedMentionEntry]


class DocumentAnalysisPromptContext(TypedDict):
    active_document: OrderedDocumentRef
    active_document_position: int
    canonical_topics_subset: list[CanonicalTopicEntry]
    canonical_tags_subset: list[CanonicalTagEntry]
    glossary_subset: list[GlossaryEntry]
    entity_subset: list[EntityRegistryEntry]
    claim_subset: list[ClaimLedgerEntry]
    reference_subset: list[ReferenceIndexEntry]
    prior_briefs_subset: list[ProcessedDocumentBrief]
    unresolved_mentions_subset: list[UnresolvedMentionEntry]
    prompt_instructions: list[str]
```

## Context Reconstruction Rules

The transient `DocumentAnalysisPromptContext` should be reconstructed from durable state using predictable rules.

Recommended rules:

1. Always include the active document.
2. Include the current canonical topics and tags only if they are relevant to the active document or recent prior documents.
3. Include glossary and entity entries by match against the active document text, prior unresolved mentions, or current topic focus.
4. Include only the most relevant prior briefs rather than the entire prior corpus.
5. Include claim and reference entries only when they help resolve continuity or cross-document grounding.
6. Keep the prompt context bounded and reproducible.

## Migration Stages

### Stage 1

Document the target architecture and make current-versus-planned boundaries explicit.

### Stage 2

Extract contracts from the current compile nodes into supervisor-era roles without changing external behavior.

### Stage 3

Wrap the existing specialist logic behind supervisor-controlled tools or subagents.

### Stage 4

Replace broad fan-out with supervisor-managed sequential document analysis and durable context updates.

### Stage 5

After supervisor behavior stabilizes, consider optional skills and optional router usage for non-core cases.

## Constraints That Must Not Change During Migration

These contracts must remain stable while the internal orchestration changes:

- `WorkflowTriggerMessage` input shape
- thread id derivation behavior
- `source_set_key` derivation behavior
- review retry and human-review semantics
- human-review resume action contract
- publish result shapes returned by the worker router
- storage-backed raw, review, and published artifacts as the durable truth boundary

## Verification Gates

Implementation should eventually prove:

1. deterministic document ordering
2. stable reconstruction of transient prompt context from durable state
3. reuse of canonical topics and tags across later documents
4. reuse of glossary and entity registry entries across later documents
5. cross-document reference resolution through `reference_index` and `claim_ledger`
6. no regressions in review escalation, publish identity, or ignored-event behavior
