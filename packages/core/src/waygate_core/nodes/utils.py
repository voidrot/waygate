import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import PurePosixPath
from typing import Any

import frontmatter
from pydantic import BaseModel

from waygate_core import get_app_context
from waygate_core.files.template import render_draft_document
from waygate_core.logging import get_logger
from waygate_core.plugin import BaseLLMProvider, StoragePlugin
from waygate_core.plugin.storage_base import StorageNamespace
from waygate_core.schema import (
    DocumentMetadataRecord,
    DraftFragment,
    DraftGenerationResult,
    DraftMergeResult,
    KnowledgeMetadata,
    MetadataExtractionResult,
    RawDocumentFrontmatter,
)

logger = get_logger()


def normalize_text_values(values: Sequence[str] | None) -> list[str]:
    if not values:
        return []

    normalized: list[str] = []
    seen: set[str] = set()

    for value in values:
        candidate = value.strip()
        if not candidate:
            continue

        key = candidate.casefold()
        if key in seen:
            continue

        seen.add(key)
        normalized.append(candidate)

    return normalized


def merge_unique_values(*value_groups: Sequence[str] | None) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()

    for group in value_groups:
        for value in group or []:
            candidate = value.strip()
            if not candidate:
                continue

            key = candidate.casefold()
            if key in seen:
                continue

            seen.add(key)
            merged.append(candidate)

    return merged


def normalize_metadata(
    metadata: KnowledgeMetadata | Mapping[str, object],
) -> KnowledgeMetadata:
    payload = (
        metadata.model_dump(mode="json", exclude_none=True)
        if isinstance(metadata, KnowledgeMetadata)
        else dict(metadata)
    )

    return KnowledgeMetadata(
        topics=coerce_text_sequence(payload.get("topics")),
        tags=coerce_text_sequence(payload.get("tags")),
        people=coerce_text_sequence(payload.get("people")),
        organizations=coerce_text_sequence(payload.get("organizations")),
        projects=coerce_text_sequence(payload.get("projects")),
        established_terms=coerce_text_sequence(payload.get("established_terms")),
    )


def merge_metadata_records(
    records: Sequence[KnowledgeMetadata | DocumentMetadataRecord],
    base: KnowledgeMetadata | None = None,
) -> KnowledgeMetadata:
    metadata_items = [normalize_metadata(base)] if base is not None else []
    metadata_items.extend(normalize_metadata(record) for record in records)

    return KnowledgeMetadata(
        topics=merge_unique_values(*(item.topics for item in metadata_items)),
        tags=merge_unique_values(*(item.tags for item in metadata_items)),
        people=merge_unique_values(*(item.people for item in metadata_items)),
        organizations=merge_unique_values(
            *(item.organizations for item in metadata_items)
        ),
        projects=merge_unique_values(*(item.projects for item in metadata_items)),
        established_terms=merge_unique_values(
            *(item.established_terms for item in metadata_items)
        ),
    )


def resolve_storage() -> StoragePlugin:
    app_context = get_app_context()
    return app_context.plugins.storage[app_context.config.core.storage_plugin_name]


def resolve_llm_provider() -> BaseLLMProvider | None:
    app_context = get_app_context()
    configured_name = app_context.config.core.llm_plugin_name
    plugin = app_context.plugins.llm.get(configured_name)
    if plugin is not None:
        return plugin

    if app_context.plugins.llm:
        first_name = next(iter(app_context.plugins.llm))
        logger.warning(
            "configured llm plugin missing, falling back to first available plugin",
            configured_name=configured_name,
            fallback_name=first_name,
        )
        return app_context.plugins.llm[first_name]

    logger.warning("no llm plugins configured for compiler workflow")
    return None


def resolve_model_name(workflow_type: str) -> str:
    core_config = get_app_context().config.core
    if workflow_type == "metadata":
        return core_config.metadata_model_name
    if workflow_type == "review":
        return core_config.review_model_name
    return core_config.draft_model_name


def read_source_document(
    doc_uri: str,
    storage: StoragePlugin | None = None,
) -> tuple[RawDocumentFrontmatter, str]:
    active_storage = storage or resolve_storage()
    raw_document = active_storage.read_document(doc_uri)
    metadata, content = frontmatter.parse(raw_document)
    metadata_dict = dict(metadata) if isinstance(metadata, Mapping) else {}

    frontmatter_model = RawDocumentFrontmatter(
        source_type=str(metadata_dict.get("source_type", "unknown")),
        source_id=_coerce_optional_string(metadata_dict.get("source_id")),
        source_hash=_coerce_optional_string(metadata_dict.get("source_hash")),
        source_uri=_coerce_optional_string(metadata_dict.get("source_uri")) or doc_uri,
        timestamp=coerce_timestamp(metadata_dict.get("timestamp")),
        topics=coerce_text_sequence(metadata_dict.get("topics")),
        tags=coerce_text_sequence(metadata_dict.get("tags")),
    )
    return frontmatter_model, content


def build_frontmatter_seed(
    frontmatter_model: RawDocumentFrontmatter,
) -> KnowledgeMetadata:
    return KnowledgeMetadata(
        topics=frontmatter_model.topics,
        tags=frontmatter_model.tags,
    )


def extract_document_metadata(
    doc_uri: str,
    content: str,
    frontmatter_model: RawDocumentFrontmatter,
    running_memory: KnowledgeMetadata,
) -> DocumentMetadataRecord:
    seed_metadata = build_frontmatter_seed(frontmatter_model)
    provider = resolve_llm_provider()

    extracted = MetadataExtractionResult(
        topics=seed_metadata.topics,
        tags=seed_metadata.tags,
        summary=f"Metadata seeded from {doc_uri}",
    )

    if provider is not None:
        prompt = build_metadata_extraction_prompt(
            doc_uri=doc_uri,
            content=content,
            frontmatter_model=frontmatter_model,
            running_memory=running_memory,
        )
        try:
            runnable = provider.get_structured_llm(
                MetadataExtractionResult,
                resolve_model_name("metadata"),
                workflow_type="draft",
            )
            extracted = runnable.invoke(prompt)
        except Exception as exc:
            logger.warning(
                "metadata extraction failed, falling back to frontmatter",
                node="metadata",
                source_document=doc_uri,
                error=str(exc),
            )

    merged = merge_metadata_records([seed_metadata, extracted])
    return DocumentMetadataRecord(
        source_document=doc_uri,
        source_type=frontmatter_model.source_type,
        source_id=frontmatter_model.source_id,
        source_uri=frontmatter_model.source_uri,
        source_hash=frontmatter_model.source_hash,
        topics=merged.topics,
        tags=merged.tags,
        people=merged.people,
        organizations=merged.organizations,
        projects=merged.projects,
        established_terms=merged.established_terms,
        summary=extracted.summary,
    )


def generate_draft_fragment(
    doc_uri: str,
    content: str,
    document_metadata: DocumentMetadataRecord,
    merged_metadata: KnowledgeMetadata,
    prior_summaries: Sequence[str],
) -> DraftFragment:
    provider = resolve_llm_provider()
    fallback_content = render_draft_document(
        context={
            **document_metadata.model_dump(mode="json", exclude_none=True),
            "merged_metadata": merged_metadata.model_dump(
                mode="json", exclude_none=True
            ),
            "prior_fragment_summaries": list(prior_summaries),
        },
        content=content,
        doc_uri=doc_uri,
    )

    result = DraftGenerationResult(
        content=fallback_content,
        summary=f"Draft fragment for {doc_uri}",
    )

    if provider is not None:
        prompt = build_draft_fragment_prompt(
            doc_uri=doc_uri,
            content=content,
            document_metadata=document_metadata,
            merged_metadata=merged_metadata,
            prior_summaries=prior_summaries,
        )
        try:
            runnable = provider.get_structured_llm(
                DraftGenerationResult,
                resolve_model_name("draft"),
                workflow_type="draft",
            )
            result = runnable.invoke(prompt)
        except Exception as exc:
            logger.warning(
                "draft fragment generation failed, falling back to rendered source",
                node="draft",
                source_document=doc_uri,
                error=str(exc),
            )

    content_value = (
        result.content.strip() if result.content.strip() else fallback_content
    )
    return DraftFragment(
        source_document=doc_uri,
        content=content_value,
        summary=result.summary or fallback_fragment_summary(content_value),
        topics=document_metadata.topics,
        tags=document_metadata.tags,
        people=document_metadata.people,
        organizations=document_metadata.organizations,
        projects=document_metadata.projects,
    )


def merge_draft_fragments(
    fragments: Sequence[DraftFragment],
    merged_metadata: KnowledgeMetadata,
) -> str:
    if not fragments:
        return ""

    fallback = "\n\n".join(fragment.content.strip() for fragment in fragments).strip()
    provider = resolve_llm_provider()
    if provider is None:
        return fallback

    prompt = build_draft_merge_prompt(
        fragments=fragments, merged_metadata=merged_metadata
    )
    try:
        runnable = provider.get_structured_llm(
            DraftMergeResult,
            resolve_model_name("draft"),
            workflow_type="draft",
        )
        merged = runnable.invoke(prompt)
        return merged.content.strip() or fallback
    except Exception as exc:
        logger.warning(
            "draft merge failed, falling back to deterministic concatenation",
            node="draft",
            error=str(exc),
        )
        return fallback


def fallback_fragment_summary(content: str) -> str:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        return "empty draft fragment"
    return lines[0][:160]


def build_metadata_extraction_prompt(
    doc_uri: str,
    content: str,
    frontmatter_model: RawDocumentFrontmatter,
    running_memory: KnowledgeMetadata,
) -> str:
    return "\n".join(
        [
            "You are extracting normalized knowledge-base metadata from one source document.",
            "Return concise values only. Do not invent entities not grounded in the source.",
            f"Source document URI: {doc_uri}",
            "Frontmatter seed:",
            serialize_payload(frontmatter_model),
            "Current merged metadata memory from earlier documents:",
            serialize_payload(running_memory),
            "Source document content:",
            content,
        ]
    )


def build_draft_fragment_prompt(
    doc_uri: str,
    content: str,
    document_metadata: DocumentMetadataRecord,
    merged_metadata: KnowledgeMetadata,
    prior_summaries: Sequence[str],
) -> str:
    return "\n".join(
        [
            "You are writing one knowledge-base draft fragment for a single source document.",
            "Use the merged metadata and prior fragment summaries as short-term memory, but ground the fragment in this source document.",
            f"Source document URI: {doc_uri}",
            "Per-document metadata:",
            serialize_payload(document_metadata),
            "Merged metadata memory:",
            serialize_payload(merged_metadata),
            "Prior fragment summaries:",
            serialize_payload(list(prior_summaries)),
            "Source document content:",
            content,
        ]
    )


def build_draft_merge_prompt(
    fragments: Sequence[DraftFragment],
    merged_metadata: KnowledgeMetadata,
) -> str:
    return "\n".join(
        [
            "You are merging document-level knowledge-base fragments into one coherent draft.",
            "Preserve grounded facts, remove duplication, and keep the result readable as a single KB document.",
            "Merged metadata:",
            serialize_payload(merged_metadata),
            "Draft fragments:",
            serialize_payload(
                [fragment.model_dump(mode="json") for fragment in fragments]
            ),
        ]
    )


def serialize_payload(payload: object) -> str:
    if isinstance(payload, BaseModel):
        data = payload.model_dump(mode="json", exclude_none=True)
    else:
        data = payload
    return json.dumps(data, indent=2, sort_keys=True, default=str)


def build_publish_document_path(trace_id: str, file_name: str | None = None) -> str:
    normalized_trace = sanitize_path_component(trace_id)
    normalized_name = sanitize_path_component(file_name or "merged-draft.md")
    relative_path = str(PurePosixPath("compiler") / normalized_trace / normalized_name)
    storage = resolve_storage()
    return storage.build_namespaced_path(StorageNamespace.Published, relative_path)


def build_publish_metadata_path(trace_id: str) -> str:
    normalized_trace = sanitize_path_component(trace_id)
    relative_path = str(
        PurePosixPath("compiler") / normalized_trace / "merged-metadata.json"
    )
    storage = resolve_storage()
    return storage.build_namespaced_path(StorageNamespace.Metadata, relative_path)


def sanitize_path_component(value: str) -> str:
    candidate = value.strip().replace("\\", "/")
    parts = [
        segment for segment in candidate.split("/") if segment not in {"", ".", ".."}
    ]
    if not parts:
        return "artifact"
    return "-".join(parts)


def coerce_text_sequence(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return normalize_text_values([value])
    if isinstance(value, Sequence):
        string_values = [item for item in value if isinstance(item, str)]
        return normalize_text_values(string_values)
    return []


def coerce_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return None


def _coerce_optional_string(value: object) -> str | None:
    if value is None:
        return None
    candidate = str(value).strip()
    return candidate or None
