from pathlib import Path

import pytest

from mcp_server.service import BriefingService, GenerateBriefingRequest
from waygate_agent_sdk import BriefingResult
from waygate_agent_sdk.models import RetrievedLiveDocument
from waygate_core.doc_helpers import generate_frontmatter
from waygate_core.schemas import FrontMatterDocument, SourceType, Visibility
from waygate_plugin_local_storage.local_storage import LocalStorageProvider


class FakeRepository:
    def __init__(self):
        self.build_calls = []
        self.retrieve_calls = []

    def build_briefing(self, request, scope=None) -> BriefingResult:
        self.build_calls.append((request, scope))
        return BriefingResult(content="briefing")

    def retrieve(self, request, scope=None) -> list[RetrievedLiveDocument]:
        self.retrieve_calls.append((request, scope))
        return []


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


def test_generate_briefing_maps_request_to_sdk_boundary() -> None:
    repository = FakeRepository()
    service = BriefingService(repository)

    result = service.generate_briefing(
        GenerateBriefingRequest(
            query="incident runbook",
            max_documents=3,
            token_budget=500,
            tags=["incident"],
            role="ops_agent",
            allowed_visibilities=[Visibility.PUBLIC],
            lineage_ids=["raw-1"],
        )
    )

    request, scope = repository.build_calls[0]
    assert result.content == "briefing"
    assert request.query == "incident runbook"
    assert request.max_documents == 3
    assert request.token_budget == 500
    assert request.tags == ["incident"]
    assert request.lineage_ids == ["raw-1"]
    assert scope.role == "ops_agent"
    assert scope.allowed_visibilities == [Visibility.PUBLIC]


def test_preview_retrieval_maps_request_to_sdk_boundary() -> None:
    repository = FakeRepository()
    service = BriefingService(repository)

    service.preview_retrieval(
        GenerateBriefingRequest(
            query="architecture",
            role="architecture_agent",
        )
    )

    request, scope = repository.retrieve_calls[0]
    assert request.query == "architecture"
    assert scope.role == "architecture_agent"


def test_generate_briefing_from_storage_uses_sdk_repository(
    storage: LocalStorageProvider,
) -> None:
    content = (
        generate_frontmatter(
            FrontMatterDocument(
                doc_id="doc-1",
                title="Deployment Runbook",
                document_type="concepts",
                source_type=SourceType.SYNTHESIS,
                status="live",
                visibility=Visibility.INTERNAL,
                tags=["ops", "runbook"],
                last_compiled="2026-04-06T12:00:00+00:00",
                last_updated="2026-04-06T12:00:00+00:00",
                lineage=["raw-1"],
                sources=["raw/raw-1"],
            )
        )
        + "\nRestart the service and verify the queue drains."
    )
    storage.write_live_document_to_category("doc-1", content, "concepts")

    service = BriefingService.from_storage(storage)
    result = service.generate_briefing(
        GenerateBriefingRequest(query="deployment runbook", token_budget=200)
    )

    assert result.documents
    assert result.documents[0].metadata.doc_id == "doc-1"
    assert "Deployment Runbook" in result.content
