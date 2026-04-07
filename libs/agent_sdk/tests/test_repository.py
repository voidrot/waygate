from pathlib import Path

import pytest

from waygate_agent_sdk import (
    DefaultVisibilityPolicy,
    LiveDocumentRepository,
    LexicalDocumentScorer,
    RetrievalQuery,
    RetrievalScope,
    estimate_tokens,
)
from waygate_core.doc_helpers import generate_frontmatter
from waygate_core.schemas import (
    DocumentStatus,
    DocumentType,
    FrontMatterDocument,
    SourceType,
    Visibility,
)
from waygate_plugin_local_storage.local_storage import LocalStorageProvider


class DenyAllVisibilityPolicy(DefaultVisibilityPolicy):
    def allows(self, metadata: FrontMatterDocument, scope: RetrievalScope) -> bool:
        return False


class ConstantScorer(LexicalDocumentScorer):
    def __init__(self, priorities: dict[str, float]):
        self.priorities = priorities

    def score(
        self,
        document,
        request: RetrievalQuery,
        lineage_ids: set[str],
    ) -> dict[str, float]:
        base = super().score(document, request, lineage_ids)
        forced_score = self.priorities.get(document.metadata.doc_id, base["score"])
        base["score"] = forced_score
        return base


class PartialScoreScorer:
    def score(
        self,
        document,
        request: RetrievalQuery,
        lineage_ids: set[str],
    ) -> dict[str, float]:
        return {"title_matches": 1.0}


@pytest.fixture()
def storage(tmp_path: Path) -> LocalStorageProvider:
    provider = LocalStorageProvider.__new__(LocalStorageProvider)
    provider.base_dir = tmp_path
    provider.raw_dir = tmp_path / "raw"
    provider.live_dir = tmp_path / "live"
    provider.staging_dir = tmp_path / "staging"
    provider.meta_dir = tmp_path / "meta"
    provider.templates_dir = provider.meta_dir / "templates"
    provider.agents_dir = provider.meta_dir / "agents"
    provider.raw_dir.mkdir()
    provider.live_dir.mkdir()
    provider.staging_dir.mkdir()
    provider.templates_dir.mkdir(parents=True)
    provider.agents_dir.mkdir(parents=True)
    return provider


def _write_live_document(
    storage: LocalStorageProvider,
    *,
    doc_id: str,
    title: str,
    body: str,
    last_compiled: str,
    visibility: Visibility = Visibility.INTERNAL,
    tags: list[str] | None = None,
    lineage: list[str] | None = None,
    document_type: DocumentType = DocumentType.CONCEPTS,
    status: DocumentStatus = DocumentStatus.LIVE,
) -> str:
    content = (
        generate_frontmatter(
            FrontMatterDocument(
                doc_id=doc_id,
                title=title,
                document_type=document_type,
                source_type=SourceType.SYNTHESIS,
                status=status,
                visibility=visibility,
                tags=tags or [],
                last_compiled=last_compiled,
                last_updated=last_compiled,
                lineage=lineage or [],
                sources=[f"raw/{doc_id}"],
            )
        )
        + f"\n{body}"
    )

    return storage.write_live_document_to_category(doc_id, content, str(document_type))


def test_estimate_tokens_is_deterministic() -> None:
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("abcde") == 2


def test_load_live_documents_parses_frontmatter_and_content(
    storage: LocalStorageProvider,
) -> None:
    uri = _write_live_document(
        storage,
        doc_id="doc-1",
        title="Incident Runbook",
        body="Step 1\nStep 2",
        last_compiled="2026-04-06T12:00:00+00:00",
    )

    repository = LiveDocumentRepository(storage)
    documents = repository.load_live_documents()

    assert len(documents) == 1
    assert documents[0].uri == uri
    assert documents[0].metadata.title == "Incident Runbook"
    assert documents[0].content == "Step 1\nStep 2"
    assert documents[0].token_estimate > 0


def test_retrieve_filters_visibility_before_ranking(
    storage: LocalStorageProvider,
) -> None:
    _write_live_document(
        storage,
        doc_id="doc-public",
        title="Public Runbook",
        body="public guidance for deployment",
        last_compiled="2026-04-06T12:00:00+00:00",
        visibility=Visibility.PUBLIC,
    )
    _write_live_document(
        storage,
        doc_id="doc-secret",
        title="Secret Runbook",
        body="deployment credentials and secrets",
        last_compiled="2026-04-06T12:05:00+00:00",
        visibility=Visibility.STRICTLY_CONFIDENTIAL,
    )

    repository = LiveDocumentRepository(storage)
    results = repository.retrieve(
        RetrievalQuery(query="runbook deployment", max_documents=10),
        RetrievalScope(allowed_visibilities=[Visibility.PUBLIC, Visibility.INTERNAL]),
    )

    assert [result.metadata.doc_id for result in results] == ["doc-public"]


def test_retrieve_applies_type_tag_and_status_filters(
    storage: LocalStorageProvider,
) -> None:
    _write_live_document(
        storage,
        doc_id="concept-live",
        title="Incident Overview",
        body="investigation summary",
        last_compiled="2026-04-06T10:00:00+00:00",
        tags=["incident", "sev1"],
        document_type=DocumentType.CONCEPTS,
        status=DocumentStatus.LIVE,
    )
    _write_live_document(
        storage,
        doc_id="entity-live",
        title="Responder Team",
        body="team ownership",
        last_compiled="2026-04-06T11:00:00+00:00",
        tags=["incident"],
        document_type=DocumentType.ENTITIES,
        status=DocumentStatus.LIVE,
    )
    _write_live_document(
        storage,
        doc_id="concept-archived",
        title="Old Incident Overview",
        body="superseded summary",
        last_compiled="2026-04-05T11:00:00+00:00",
        tags=["incident", "sev1"],
        document_type=DocumentType.CONCEPTS,
        status=DocumentStatus.ARCHIVED,
    )

    repository = LiveDocumentRepository(storage)
    results = repository.retrieve(
        RetrievalQuery(
            query="incident",
            document_types=[DocumentType.CONCEPTS],
            tags=["incident", "sev1"],
            max_documents=10,
        )
    )

    assert [result.metadata.doc_id for result in results] == ["concept-live"]


def test_retrieve_ranks_by_score_then_recency(storage: LocalStorageProvider) -> None:
    _write_live_document(
        storage,
        doc_id="doc-older",
        title="Incident Notes",
        body="runbook details",
        last_compiled="2026-04-06T09:00:00+00:00",
    )
    _write_live_document(
        storage,
        doc_id="doc-newer",
        title="Incident Notes",
        body="runbook details",
        last_compiled="2026-04-06T12:00:00+00:00",
    )
    _write_live_document(
        storage,
        doc_id="doc-best",
        title="Incident Runbook",
        body="runbook details and checklist",
        last_compiled="2026-04-06T08:00:00+00:00",
        tags=["incident", "runbook"],
    )

    repository = LiveDocumentRepository(storage)
    results = repository.retrieve(
        RetrievalQuery(query="incident runbook", max_documents=10)
    )

    assert [result.metadata.doc_id for result in results] == [
        "doc-best",
        "doc-newer",
        "doc-older",
    ]


def test_retrieve_supports_lineage_filter(storage: LocalStorageProvider) -> None:
    _write_live_document(
        storage,
        doc_id="doc-a",
        title="Architecture Summary",
        body="summary body",
        last_compiled="2026-04-06T12:00:00+00:00",
        lineage=["raw-a"],
    )
    _write_live_document(
        storage,
        doc_id="doc-b",
        title="Architecture Deep Dive",
        body="deep dive body",
        last_compiled="2026-04-06T12:10:00+00:00",
        lineage=["raw-b"],
    )

    repository = LiveDocumentRepository(storage)
    results = repository.retrieve(
        RetrievalQuery(query="architecture", lineage_ids=["raw-b"], max_documents=10)
    )

    assert [result.metadata.doc_id for result in results] == ["doc-b"]


def test_build_briefing_honors_token_budget(storage: LocalStorageProvider) -> None:
    _write_live_document(
        storage,
        doc_id="doc-1",
        title="Service Runbook",
        body=("step\n" * 120).strip(),
        last_compiled="2026-04-06T12:00:00+00:00",
        tags=["runbook"],
    )
    _write_live_document(
        storage,
        doc_id="doc-2",
        title="Service Checklist",
        body=("check\n" * 120).strip(),
        last_compiled="2026-04-06T12:05:00+00:00",
        tags=["runbook"],
    )

    repository = LiveDocumentRepository(storage)
    result = repository.build_briefing(
        RetrievalQuery(query="service runbook", max_documents=10, token_budget=80)
    )

    assert result.documents
    assert result.truncated is True
    assert result.total_token_estimate <= 80
    assert "## Service Runbook" in result.content


def test_retrieve_supports_custom_visibility_policy(
    storage: LocalStorageProvider,
) -> None:
    _write_live_document(
        storage,
        doc_id="doc-1",
        title="Public Doc",
        body="useful text",
        last_compiled="2026-04-06T12:00:00+00:00",
        visibility=Visibility.PUBLIC,
    )

    repository = LiveDocumentRepository(
        storage,
        visibility_policy=DenyAllVisibilityPolicy(),
    )
    results = repository.retrieve(RetrievalQuery(query="public"))

    assert results == []


def test_retrieve_supports_custom_scorer(storage: LocalStorageProvider) -> None:
    _write_live_document(
        storage,
        doc_id="doc-low",
        title="Runbook Alpha",
        body="alpha body",
        last_compiled="2026-04-06T12:00:00+00:00",
    )
    _write_live_document(
        storage,
        doc_id="doc-high",
        title="Runbook Beta",
        body="beta body",
        last_compiled="2026-04-06T11:00:00+00:00",
    )

    repository = LiveDocumentRepository(
        storage,
        scorer=ConstantScorer({"doc-high": 999.0, "doc-low": 1.0}),
    )
    results = repository.retrieve(RetrievalQuery(query="runbook", max_documents=10))

    assert [result.metadata.doc_id for result in results] == ["doc-high", "doc-low"]


def test_retrieve_tolerates_partial_custom_score_breakdown(
    storage: LocalStorageProvider,
) -> None:
    _write_live_document(
        storage,
        doc_id="doc-partial",
        title="Reference Document",
        body="reference body",
        last_compiled="2026-04-06T12:00:00+00:00",
    )

    repository = LiveDocumentRepository(
        storage,
        scorer=PartialScoreScorer(),
    )
    results = repository.retrieve(RetrievalQuery(query="", max_documents=10))

    assert len(results) == 1
    assert results[0].metadata.doc_id == "doc-partial"
    assert results[0].score == 0.0
    assert results[0].score_breakdown["lexical_score"] == 0.0
    assert results[0].score_breakdown["score"] == 0.0
