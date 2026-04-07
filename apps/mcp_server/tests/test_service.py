from pathlib import Path

import pytest

from mcp_server.service import (
    BriefingService,
    GenerateBriefingRequest,
    ReportContextErrorRequest,
)
from mcp_server.trace import reset_current_trace_id, set_current_trace_id
from waygate_agent_sdk import BriefingResult
from waygate_agent_sdk.models import RetrievalScope
from waygate_agent_sdk.models import RetrievedLiveDocument
from waygate_core.doc_helpers import generate_frontmatter
from waygate_core.schemas import (
    AuditEventType,
    FrontMatterDocument,
    MaintenanceFindingType,
    SourceType,
    Visibility,
)
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


class FakeAuditStorage:
    def __init__(self) -> None:
        self.audit_events = []
        self.maintenance_findings = []

    def write_audit_event(self, event) -> str:
        self.audit_events.append(event)
        return f"meta/audit/{event.event_id}"

    def write_maintenance_finding(self, finding) -> str:
        self.maintenance_findings.append(finding)
        return f"meta/maintenance/{finding.finding_id}"


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
    service = BriefingService(
        repository,
        default_scope=RetrievalScope(
            role="server_role",
            allowed_visibilities=[Visibility.PUBLIC],
        ),
    )

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
    assert scope.role == "server_role"
    assert scope.allowed_visibilities == [Visibility.PUBLIC]


def test_preview_retrieval_maps_request_to_sdk_boundary() -> None:
    repository = FakeRepository()
    service = BriefingService(
        repository,
        default_scope=RetrievalScope(
            role="preview_role",
            allowed_visibilities=[Visibility.PUBLIC],
        ),
    )

    service.preview_retrieval(
        GenerateBriefingRequest(
            query="architecture",
            role="architecture_agent",
        )
    )

    request, scope = repository.retrieve_calls[0]
    assert request.query == "architecture"
    assert scope.role == "preview_role"


def test_generate_briefing_writes_retrieval_audit_event() -> None:
    repository = FakeRepository()
    audit_storage = FakeAuditStorage()
    service = BriefingService(
        repository,
        default_scope=RetrievalScope(
            role="ops_agent",
            allowed_visibilities=[Visibility.PUBLIC],
        ),
        audit_storage=audit_storage,
    )

    service.generate_briefing(
        GenerateBriefingRequest(
            query="incident runbook",
            role="ignored_role",
            allowed_visibilities=[Visibility.PUBLIC, Visibility.INTERNAL],
        )
    )

    assert len(audit_storage.audit_events) == 1
    event = audit_storage.audit_events[0]
    assert event.event_type == AuditEventType.MCP_RETRIEVAL_REQUESTED
    assert event.payload["action"] == "generate_briefing"
    assert event.payload["role"] == "ops_agent"
    assert event.payload["allowed_visibilities"] == ["public"]
    assert event.payload["requested_allowed_visibilities"] == ["public", "internal"]


def test_generate_briefing_includes_current_trace_id_in_audit_event() -> None:
    repository = FakeRepository()
    audit_storage = FakeAuditStorage()
    service = BriefingService(repository, audit_storage=audit_storage)
    token = set_current_trace_id("trace-mcp-1")

    try:
        service.generate_briefing(GenerateBriefingRequest(query="incident runbook"))
    finally:
        reset_current_trace_id(token)

    assert len(audit_storage.audit_events) == 1
    assert audit_storage.audit_events[0].trace_id == "trace-mcp-1"


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


def test_report_context_error_persists_maintenance_finding() -> None:
    repository = FakeRepository()
    meta_storage = FakeAuditStorage()
    service = BriefingService(
        repository,
        default_scope=RetrievalScope(
            role="ops_agent",
            allowed_visibilities=[Visibility.PUBLIC],
        ),
        maintenance_storage=meta_storage,
    )
    token = set_current_trace_id("trace-gap-1")

    try:
        finding_uri = service.report_context_error(
            ReportContextErrorRequest(
                message="Missing escalation policy for database failover",
                query="database failover escalation policy",
                role="ignored_role",
                allowed_visibilities=[Visibility.PUBLIC, Visibility.INTERNAL],
                lineage_ids=["raw-9"],
                tags=["ops", "database"],
            )
        )
    finally:
        reset_current_trace_id(token)

    assert finding_uri.startswith("meta/maintenance/")
    assert len(meta_storage.maintenance_findings) == 1
    finding = meta_storage.maintenance_findings[0]
    assert finding.finding_type == MaintenanceFindingType.CONTEXT_ERROR
    assert finding.trace_id == "trace-gap-1"
    assert finding.related_doc_ids == ["raw-9"]
    assert finding.payload["message"] == "Missing escalation policy for database failover"
    assert finding.payload["role"] == "ops_agent"
    assert finding.payload["requested_visibilities"] == ["public"]


def test_report_context_error_from_storage_writes_local_artifact(
    storage: LocalStorageProvider,
) -> None:
    service = BriefingService.from_storage(storage)
    token = set_current_trace_id("trace-gap-2")

    try:
        finding_uri = service.report_context_error(
            ReportContextErrorRequest(
                message="Need deployment rollback checklist",
                query="deployment rollback checklist",
                tags=["release"],
            )
        )
    finally:
        reset_current_trace_id(token)

    saved = storage.read_maintenance_finding(finding_uri)
    assert saved.finding_type == MaintenanceFindingType.CONTEXT_ERROR
    assert saved.trace_id == "trace-gap-2"
    assert saved.payload["query"] == "deployment rollback checklist"
    assert saved.payload["tags"] == ["release"]
