from typing import Protocol
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from waygate_agent_sdk import BriefingResult, LiveDocumentRepository
from waygate_agent_sdk.models import (
    RetrievalQuery,
    RetrievalScope,
    RetrievedLiveDocument,
)
from waygate_core.maintenance import record_context_error
from waygate_core.observability import start_span
from waygate_core.schemas import (
    AuditEvent,
    AuditEventType,
    ContextErrorReport,
    DocumentStatus,
    DocumentType,
    Visibility,
)
from waygate_storage.storage_base import StorageProvider
from mcp_server.trace import get_current_trace_id


class GenerateBriefingRequest(BaseModel):
    query: str = ""
    max_documents: int = Field(default=5, ge=1)
    token_budget: int = Field(default=4000, ge=1)
    tags: list[str] = Field(default_factory=list)
    document_types: list[DocumentType | str] = Field(default_factory=list)
    statuses: list[DocumentStatus | str] = Field(
        default_factory=lambda: [DocumentStatus.LIVE, DocumentStatus.ACTIVE]
    )
    lineage_ids: list[str] = Field(default_factory=list)
    role: str | None = None
    allowed_visibilities: list[Visibility] = Field(
        default_factory=lambda: [Visibility.PUBLIC, Visibility.INTERNAL]
    )

    def to_retrieval_query(self) -> RetrievalQuery:
        return RetrievalQuery(
            query=self.query,
            max_documents=self.max_documents,
            token_budget=self.token_budget,
            tags=self.tags,
            document_types=self.document_types,
            statuses=self.statuses,
            lineage_ids=self.lineage_ids,
        )

    def to_retrieval_scope(self) -> RetrievalScope:
        return RetrievalScope(
            role=self.role,
            allowed_visibilities=self.allowed_visibilities,
        )


class ReportContextErrorRequest(BaseModel):
    message: str = Field(min_length=1)
    query: str = ""
    lineage_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    role: str | None = None
    allowed_visibilities: list[Visibility] = Field(
        default_factory=lambda: [Visibility.PUBLIC, Visibility.INTERNAL]
    )


class BriefingRepository(Protocol):
    def build_briefing(
        self, request: RetrievalQuery, scope: RetrievalScope | None = None
    ) -> BriefingResult: ...

    def retrieve(
        self, request: RetrievalQuery, scope: RetrievalScope | None = None
    ) -> list[RetrievedLiveDocument]: ...


class BriefingService:
    def __init__(
        self,
        repository: BriefingRepository,
        default_scope: RetrievalScope | None = None,
        audit_storage: StorageProvider | None = None,
        maintenance_storage: StorageProvider | None = None,
    ):
        self.repository = repository
        self.default_scope = default_scope
        self.audit_storage = audit_storage
        self.maintenance_storage = maintenance_storage or audit_storage

    @classmethod
    def from_storage(
        cls,
        storage_provider: StorageProvider,
        default_scope: RetrievalScope | None = None,
    ) -> "BriefingService":
        return cls(
            LiveDocumentRepository(storage_provider),
            default_scope=default_scope,
            audit_storage=storage_provider,
            maintenance_storage=storage_provider,
        )

    def _resolve_scope_values(
        self,
        request_role: str | None,
        request_allowed_visibilities: list[Visibility],
    ) -> RetrievalScope:
        if self.default_scope is None:
            return RetrievalScope(
                role=request_role,
                allowed_visibilities=request_allowed_visibilities,
            )

        allowed_values = {
            str(item) for item in self.default_scope.allowed_visibilities
        }
        effective_allowed_visibilities = [
            item
            for item in request_allowed_visibilities
            if str(item) in allowed_values
        ]
        return RetrievalScope(
            role=(
                self.default_scope.role
                if self.default_scope.role is not None
                else request_role
            ),
            allowed_visibilities=effective_allowed_visibilities,
        )

    def _resolve_scope(self, request: GenerateBriefingRequest) -> RetrievalScope:
        return self._resolve_scope_values(
            request.role,
            request.allowed_visibilities,
        )

    def _write_retrieval_audit_event(
        self,
        request: GenerateBriefingRequest,
        scope: RetrievalScope,
        action: str,
    ) -> None:
        if self.audit_storage is None:
            return

        self.audit_storage.write_audit_event(
            AuditEvent(
                event_type=AuditEventType.MCP_RETRIEVAL_REQUESTED,
                occurred_at=datetime.now(timezone.utc).isoformat(),
                trace_id=get_current_trace_id(),
                payload={
                    "action": action,
                    "query": request.query,
                    "role": scope.role,
                    "allowed_visibilities": [
                        str(item) for item in scope.allowed_visibilities
                    ],
                    "requested_role": request.role,
                    "requested_allowed_visibilities": [
                        str(item) for item in request.allowed_visibilities
                    ],
                },
            )
        )

    def generate_briefing(self, request: GenerateBriefingRequest) -> BriefingResult:
        scope = self._resolve_scope(request)
        with start_span(
            "mcp.generate_briefing",
            tracer_name=__name__,
            attributes={
                "waygate.trace_id": get_current_trace_id(),
                "waygate.query": request.query,
                "waygate.max_documents": request.max_documents,
                "waygate.token_budget": request.token_budget,
                "waygate.role": scope.role,
                "waygate.allowed_visibilities": ",".join(
                    str(item) for item in scope.allowed_visibilities
                ),
                "waygate.lineage_count": len(request.lineage_ids),
            },
        ) as span:
            self._write_retrieval_audit_event(request, scope, "generate_briefing")
            result = self.repository.build_briefing(
                request.to_retrieval_query(),
                scope,
            )
            span.set_attribute("waygate.document_count", len(result.documents))
            return result

    def preview_retrieval(
        self, request: GenerateBriefingRequest
    ) -> list[RetrievedLiveDocument]:
        scope = self._resolve_scope(request)
        with start_span(
            "mcp.preview_retrieval",
            tracer_name=__name__,
            attributes={
                "waygate.trace_id": get_current_trace_id(),
                "waygate.query": request.query,
                "waygate.max_documents": request.max_documents,
                "waygate.role": scope.role,
                "waygate.allowed_visibilities": ",".join(
                    str(item) for item in scope.allowed_visibilities
                ),
                "waygate.lineage_count": len(request.lineage_ids),
            },
        ) as span:
            self._write_retrieval_audit_event(request, scope, "preview_retrieval")
            results = self.repository.retrieve(
                request.to_retrieval_query(),
                scope,
            )
            span.set_attribute("waygate.document_count", len(results))
            return results

    def report_context_error(self, request: ReportContextErrorRequest) -> str:
        if self.maintenance_storage is None:
            raise RuntimeError("Context-error reporting requires a storage provider")

        scope = self._resolve_scope_values(
            request.role,
            request.allowed_visibilities,
        )

        with start_span(
            "mcp.report_context_error",
            tracer_name=__name__,
            attributes={
                "waygate.trace_id": get_current_trace_id(),
                "waygate.query": request.query,
                "waygate.role": scope.role,
                "waygate.allowed_visibilities": ",".join(
                    str(item) for item in scope.allowed_visibilities
                ),
                "waygate.lineage_count": len(request.lineage_ids),
                "waygate.tag_count": len(request.tags),
            },
        ) as span:
            report = ContextErrorReport(
                occurred_at=datetime.now(timezone.utc).isoformat(),
                message=request.message,
                trace_id=get_current_trace_id(),
                query=request.query,
                role=scope.role,
                requested_visibilities=scope.allowed_visibilities,
                lineage_ids=request.lineage_ids,
                tags=request.tags,
            )
            finding_uri = record_context_error(self.maintenance_storage, report)
            span.set_attribute("waygate.finding_uri", finding_uri)
            return finding_uri
