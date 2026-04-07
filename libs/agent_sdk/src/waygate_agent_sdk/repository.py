from __future__ import annotations

from datetime import UTC, datetime

import frontmatter

from waygate_core.schemas import FrontMatterDocument
from waygate_storage.storage_base import StorageProvider

from waygate_agent_sdk.models import (
    BriefingResult,
    LoadedLiveDocument,
    RetrievalQuery,
    RetrievalScope,
    RetrievedLiveDocument,
)
from waygate_agent_sdk.policy import DefaultVisibilityPolicy, VisibilityPolicy
from waygate_agent_sdk.scoring import DocumentScorer, LexicalDocumentScorer, tokenize

TOKEN_CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return (len(text) + TOKEN_CHARS_PER_TOKEN - 1) // TOKEN_CHARS_PER_TOKEN


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _normalize_live_metadata(metadata: dict) -> dict:
    normalized = dict(metadata)
    for field_name in ("last_compiled", "last_updated"):
        value = normalized.get(field_name)
        if isinstance(value, datetime):
            normalized[field_name] = value.isoformat()
    if normalized.get("source_metadata") == {}:
        normalized["source_metadata"] = None
    return normalized


class LiveDocumentRepository:
    def __init__(
        self,
        storage_provider: StorageProvider,
        visibility_policy: VisibilityPolicy | None = None,
        scorer: DocumentScorer | None = None,
    ):
        self.storage = storage_provider
        self.visibility_policy = visibility_policy or DefaultVisibilityPolicy()
        self.scorer = scorer or LexicalDocumentScorer()

    def load_live_documents(self, prefix: str = "") -> list[LoadedLiveDocument]:
        documents: list[LoadedLiveDocument] = []
        for uri in sorted(self.storage.list_live_documents(prefix)):
            raw_markdown = self.storage.read_live_document(uri)
            post = frontmatter.loads(raw_markdown)
            metadata = _normalize_live_metadata(dict(post.metadata))

            documents.append(
                LoadedLiveDocument(
                    uri=uri,
                    metadata=FrontMatterDocument.model_validate(metadata),
                    content=post.content,
                    token_estimate=estimate_tokens(raw_markdown),
                )
            )
        return documents

    def retrieve(
        self, request: RetrievalQuery, scope: RetrievalScope | None = None
    ) -> list[RetrievedLiveDocument]:
        scope = scope or RetrievalScope()
        required_tags = {tag.lower() for tag in request.tags}
        required_types = {
            str(document_type) for document_type in request.document_types
        }
        allowed_statuses = {str(status) for status in request.statuses}
        lineage_ids = set(request.lineage_ids)
        matches: list[RetrievedLiveDocument] = []
        query_terms = tokenize(request.query)

        for document in self.load_live_documents():
            metadata = document.metadata

            if not self.visibility_policy.allows(metadata, scope):
                continue
            if required_types and str(metadata.document_type) not in required_types:
                continue
            if allowed_statuses and str(metadata.status) not in allowed_statuses:
                continue
            if required_tags and not required_tags.issubset(
                {tag.lower() for tag in metadata.tags}
            ):
                continue
            if lineage_ids and not lineage_ids.intersection(metadata.lineage):
                continue

            breakdown = self.scorer.score(document, request, lineage_ids)
            if query_terms and breakdown["lexical_score"] == 0:
                continue

            matches.append(
                RetrievedLiveDocument(
                    **document.model_dump(),
                    score=breakdown["score"],
                    score_breakdown=breakdown,
                )
            )

        matches.sort(
            key=lambda document: (
                -document.score,
                -self._recency_value(document.metadata),
                document.metadata.title.lower(),
                document.uri,
            )
        )
        return matches[: request.max_documents]

    def build_briefing(
        self, request: RetrievalQuery, scope: RetrievalScope | None = None
    ) -> BriefingResult:
        ranked_documents = self.retrieve(request, scope)
        remaining_tokens = request.token_budget
        selected_documents: list[RetrievedLiveDocument] = []
        sections: list[str] = []
        truncated = False

        for document in ranked_documents:
            section = self._render_section(document)
            section_tokens = estimate_tokens(section)

            if section_tokens <= remaining_tokens:
                selected_documents.append(document)
                sections.append(section)
                remaining_tokens -= section_tokens
                continue

            partial = self._render_section(document, max_tokens=remaining_tokens)
            if partial:
                selected_documents.append(document)
                sections.append(partial)
                remaining_tokens = 0
            truncated = True
            break

        total_tokens = request.token_budget - remaining_tokens
        return BriefingResult(
            documents=selected_documents,
            content="\n\n".join(sections),
            total_token_estimate=total_tokens,
            truncated=truncated,
        )

    def _recency_value(self, metadata: FrontMatterDocument) -> float:
        timestamp = _parse_timestamp(metadata.last_compiled) or _parse_timestamp(
            metadata.last_updated
        )
        return timestamp.timestamp() if timestamp else 0.0

    def _render_section(
        self, document: RetrievedLiveDocument, max_tokens: int | None = None
    ) -> str:
        metadata = document.metadata
        header_lines = [
            f"## {metadata.title}",
            f"- doc_id: {metadata.doc_id}",
            f"- uri: {document.uri}",
            f"- document_type: {metadata.document_type}",
            f"- visibility: {metadata.visibility}",
        ]
        if metadata.tags:
            header_lines.append(f"- tags: {', '.join(metadata.tags)}")
        if metadata.sources:
            header_lines.append(f"- sources: {', '.join(metadata.sources)}")

        header = "\n".join(header_lines) + "\n\n"
        body = document.content.strip()
        section = header + body
        if max_tokens is None:
            return section

        allowed_chars = max_tokens * TOKEN_CHARS_PER_TOKEN
        if allowed_chars <= len(header):
            return ""
        if len(section) <= allowed_chars:
            return section

        trimmed_body = body[: max(0, allowed_chars - len(header) - 1)].rstrip()
        if not trimmed_body:
            return ""
        return header + trimmed_body + "…"
