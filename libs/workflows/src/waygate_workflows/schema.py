from __future__ import annotations

import hashlib
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field
from typing_extensions import TypedDict


def _dedupe_strings(values: list[str]) -> list[str]:
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
    return " ".join(value.strip().lower().split())


def claim_id_for_text(text: str) -> str:
    normalized = normalize_key(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]


class WorkflowType(StrEnum):
    DRAFT = "draft"
    REVIEW = "review"


class WorkflowEvent(StrEnum):
    DRAFT_READY = "draft.ready"
    DRAFT_IN_PROGRESS = "draft.in_progress"
    DRAFT_COMPLETED = "draft.completed"
    REVIEW_READY = "review.ready"
    REVIEW_IN_PROGRESS = "review.in_progress"
    REVIEW_COMPLETED = "review.completed"


class DraftWorkflowStatus(StrEnum):
    READY = "ready"
    COMPILING = "compiling"
    REVIEW = "review"
    REJECTED = "rejected"
    APPROVED = "approved"
    HUMAN_REVIEW = "human_review"
    PUBLISHED = "published"


class ScratchpadState(TypedDict):
    terms: list[str]
    claims: list[str]


class SourceDocumentState(TypedDict):
    uri: str
    content: str
    source_hash: str | None
    source_uri: str | None
    source_type: str | None
    timestamp: str | None


class OrderedDocumentRef(TypedDict):
    uri: str
    source_hash: str | None
    source_uri: str | None
    source_type: str | None
    timestamp: str | None


class DocumentMetadataState(TypedDict):
    uri: str
    tags: list[str]
    topics: list[str]
    people: list[str]
    organizations: list[str]
    projects: list[str]


class DocumentSummaryState(TypedDict):
    uri: str
    summary: str
    key_claims: list[str]
    defined_terms: list[str]


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


class DocumentAnalysisPromptContext(TypedDict):
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
    approved: bool
    feedback: list[str]


class MetadataExtractionModel(BaseModel):
    tags: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    people: list[str] = Field(default_factory=list)
    organizations: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)


class SummaryExtractionModel(BaseModel):
    summary: str
    key_claims: list[str] = Field(default_factory=list)
    defined_terms: list[str] = Field(default_factory=list)


class FindingsExtractionModel(BaseModel):
    key_claims: list[str] = Field(default_factory=list)
    defined_terms: list[str] = Field(default_factory=list)


class ContinuityMentionModel(BaseModel):
    raw_text: str
    kind_hint: str | None = None


class ContinuityExtractionModel(BaseModel):
    referenced_entities: list[str] = Field(default_factory=list)
    unresolved_mentions: list[ContinuityMentionModel] = Field(default_factory=list)


class DocumentAnalysisResultModel(BaseModel):
    uri: str
    metadata: MetadataExtractionModel
    summary: SummaryExtractionModel
    findings: FindingsExtractionModel = Field(default_factory=FindingsExtractionModel)
    continuity: ContinuityExtractionModel = Field(
        default_factory=ContinuityExtractionModel
    )


class ReviewOutcomeModel(BaseModel):
    approved: bool
    feedback: list[str] = Field(default_factory=list)


class DraftGraphState(TypedDict):
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
    published_document_uri: str | None
    published_document_id: str | None
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
