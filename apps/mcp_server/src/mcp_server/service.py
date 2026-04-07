from typing import Protocol
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from waygate_agent_sdk import BriefingResult, LiveDocumentRepository
from waygate_agent_sdk.models import (
    RetrievalQuery,
    RetrievalScope,
    RetrievedLiveDocument,
)
from waygate_core.schemas import (
    AuditEvent,
    AuditEventType,
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
    ):
        self.repository = repository
        self.default_scope = default_scope
        self.audit_storage = audit_storage

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
        )

    def _resolve_scope(self, request: GenerateBriefingRequest) -> RetrievalScope:
        if self.default_scope is not None:
            return RetrievalScope.model_validate(self.default_scope.model_dump())
        return request.to_retrieval_scope()

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
        self._write_retrieval_audit_event(request, scope, "generate_briefing")
        return self.repository.build_briefing(
            request.to_retrieval_query(),
            scope,
        )

    def preview_retrieval(
        self, request: GenerateBriefingRequest
    ) -> list[RetrievedLiveDocument]:
        scope = self._resolve_scope(request)
        self._write_retrieval_audit_event(request, scope, "preview_retrieval")
        return self.repository.retrieve(
            request.to_retrieval_query(),
            scope,
        )
