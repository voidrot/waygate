from __future__ import annotations

import hashlib
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field
from typing_extensions import TypedDict


def _dedupe_strings(values: list[str]) -> list[str]:
    """Remove empty and duplicate strings while preserving order.

    Args:
        values: Raw string values that may contain duplicates or whitespace.

    Returns:
        Deduplicated string values in first-seen order.
    """
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def normalize_key(value: str) -> str:
    """Normalize free-form text for case-insensitive key comparisons.

    Args:
        value: Arbitrary text value.

    Returns:
        Lowercased, whitespace-normalized comparison key.
    """
    return " ".join(value.strip().lower().split())


def claim_id_for_text(text: str) -> str:
    """Build a stable short claim id from claim text.

    Args:
        text: Claim text extracted from source analysis.

    Returns:
        Short deterministic identifier derived from normalized claim text.
    """
    normalized = normalize_key(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]


class WorkflowType(StrEnum):
    """High-level workflow families supported by the worker runtime."""

    DRAFT = "draft"
    REVIEW = "review"


class WorkflowEvent(StrEnum):
    """Workflow trigger and lifecycle event names."""

    DRAFT_READY = "draft.ready"
    READY_INTEGRATE = "ready.integrate"
    DRAFT_IN_PROGRESS = "draft.in_progress"
    DRAFT_COMPLETED = "draft.completed"
    REVIEW_READY = "review.ready"
    REVIEW_IN_PROGRESS = "review.in_progress"
    REVIEW_COMPLETED = "review.completed"


class DraftWorkflowStatus(StrEnum):
    """Draft compile statuses persisted in workflow state."""

    READY = "ready"
    COMPILING = "compiling"
    REVIEW = "review"
    REJECTED = "rejected"
    APPROVED = "approved"
    HUMAN_REVIEW = "human_review"
    PUBLISHED = "published"


class ScratchpadState(TypedDict):
    """Legacy scratchpad fields retained for downstream compatibility."""

    terms: list[str]
    claims: list[str]


class SourceDocumentState(TypedDict):
    """Normalized raw document content and frontmatter used by compile."""

    uri: str
    content: str
    content_hash: str | None
    source_hash: str | None
    source_uri: str | None
    source_type: str | None
    timestamp: str | None


class OrderedDocumentRef(TypedDict):
    """Lightweight durable reference for document ordering state."""

    uri: str
    content_hash: str | None
    source_hash: str | None
    source_uri: str | None
    source_type: str | None
    timestamp: str | None


class DocumentMetadataState(TypedDict):
    """Metadata extracted for one source document."""

    uri: str
    tags: list[str]
    topics: list[str]
    people: list[str]
    organizations: list[str]
    projects: list[str]


class DocumentSummaryState(TypedDict):
    """Narrative summary and grounded findings for one source document."""

    uri: str
    summary: str
    key_claims: list[str]
    defined_terms: list[str]


class ProcessedDocumentBrief(TypedDict):
    """Condensed durable brief retained after each source-analysis pass."""

    uri: str
    summary: str
    key_claims: list[str]
    defined_terms: list[str]
    discovered_topics: list[str]
    discovered_tags: list[str]
    referenced_entities: list[str]
    supporting_source_uris: list[str]


class CanonicalTopicEntry(TypedDict):
    """Canonicalized topic entry accumulated across documents."""

    name: str
    aliases: list[str]
    supporting_source_uris: list[str]


class CanonicalTagEntry(TypedDict):
    """Canonicalized tag entry accumulated across documents."""

    name: str
    aliases: list[str]
    supporting_source_uris: list[str]


class GlossaryEntry(TypedDict):
    """Glossary term discovered during sequential source analysis."""

    term: str
    aliases: list[str]
    definition_hint: str | None
    supporting_source_uris: list[str]


class EntityRegistryEntry(TypedDict):
    """Canonical entity registry entry for a person, organization, or project."""

    kind: Literal["person", "organization", "project"]
    canonical_name: str
    aliases: list[str]
    supporting_source_uris: list[str]


class ClaimLedgerEntry(TypedDict):
    """Grounded claim retained for later synthesis and continuity resolution."""

    claim_id: str
    text: str
    supporting_source_uris: list[str]
    related_entities: list[str]
    related_terms: list[str]


class ReferenceIndexEntry(TypedDict):
    """Reference lookup entry used to reconnect later documents to prior context."""

    key: str
    kind: Literal["term", "entity", "claim"]
    source_uris: list[str]
    processed_document_uris: list[str]
    claim_ids: list[str]


class UnresolvedMentionEntry(TypedDict):
    """Durable record of a mention that may be resolved by later documents."""

    raw_text: str
    kind_hint: str | None
    source_uri: str
    status: Literal["open", "resolved", "dropped"]


class DocumentAnalysisPromptContext(TypedDict):
    """Bounded prompt context reconstructed for one analysis pass."""

    active_document: SourceDocumentState
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


class ReviewOutcomeState(TypedDict):
    """Review decision persisted in graph state."""

    approved: bool
    feedback: list[str]


class MetadataExtractionModel(BaseModel):
    """Structured metadata extracted for one source document."""

    tags: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    people: list[str] = Field(default_factory=list)
    organizations: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)


class SummaryExtractionModel(BaseModel):
    """Structured narrative summary for one source document."""

    summary: str
    key_claims: list[str] = Field(default_factory=list)
    defined_terms: list[str] = Field(default_factory=list)


class FindingsExtractionModel(BaseModel):
    """Structured grounded claims and defined terms for one source document."""

    key_claims: list[str] = Field(default_factory=list)
    defined_terms: list[str] = Field(default_factory=list)


class ContinuityMentionModel(BaseModel):
    """One unresolved mention emitted by the continuity specialist."""

    raw_text: str
    kind_hint: str | None = None


class ContinuityExtractionModel(BaseModel):
    """Structured continuity output for one source document."""

    referenced_entities: list[str] = Field(default_factory=list)
    unresolved_mentions: list[ContinuityMentionModel] = Field(default_factory=list)


class DocumentAnalysisResultModel(BaseModel):
    """Combined output returned by the source-analysis supervisor."""

    uri: str
    metadata: MetadataExtractionModel
    summary: SummaryExtractionModel
    findings: FindingsExtractionModel = Field(default_factory=FindingsExtractionModel)
    continuity: ContinuityExtractionModel = Field(
        default_factory=ContinuityExtractionModel
    )


class ReviewOutcomeModel(BaseModel):
    """Structured review outcome returned by the review specialist."""

    approved: bool
    feedback: list[str] = Field(default_factory=list)


class DraftGraphState(TypedDict):
    """Complete LangGraph state for the draft compile workflow."""

    workflow_type: WorkflowType
    event_type: WorkflowEvent
    source: str
    raw_documents: list[str]
    source_documents: list[SourceDocumentState]
    document_order: list[OrderedDocumentRef]
    document_cursor: int
    active_document: SourceDocumentState | None
    source_set_key: str | None
    revision_count: int
    status: DraftWorkflowStatus
    scratchpad: ScratchpadState
    extracted_metadata: list[DocumentMetadataState]
    document_summaries: list[DocumentSummaryState]
    prior_document_briefs: list[ProcessedDocumentBrief]
    canonical_topics: list[CanonicalTopicEntry]
    canonical_tags: list[CanonicalTagEntry]
    glossary: list[GlossaryEntry]
    entity_registry: list[EntityRegistryEntry]
    claim_ledger: list[ClaimLedgerEntry]
    reference_index: list[ReferenceIndexEntry]
    unresolved_mentions: list[UnresolvedMentionEntry]
    current_draft: str
    review_feedback: list[str]
    review_outcome: ReviewOutcomeState | None
    compiled_document_uri: str | None
    compiled_document_id: str | None
    compiled_document_hash: str | None
    human_review_record_uri: str | None
    human_review_action: str | None


__all__ = [
    "CanonicalTagEntry",
    "CanonicalTopicEntry",
    "ClaimLedgerEntry",
    "DocumentAnalysisResultModel",
    "DocumentAnalysisPromptContext",
    "DocumentMetadataState",
    "DocumentSummaryState",
    "DraftGraphState",
    "DraftWorkflowStatus",
    "EntityRegistryEntry",
    "GlossaryEntry",
    "MetadataExtractionModel",
    "OrderedDocumentRef",
    "ProcessedDocumentBrief",
    "ReferenceIndexEntry",
    "ReviewOutcomeModel",
    "ReviewOutcomeState",
    "ScratchpadState",
    "SourceDocumentState",
    "SummaryExtractionModel",
    "UnresolvedMentionEntry",
    "WorkflowEvent",
    "WorkflowType",
    "claim_id_for_text",
    "normalize_key",
    "FindingsExtractionModel",
    "ContinuityExtractionModel",
    "ContinuityMentionModel",
]
