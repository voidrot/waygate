from typing import Protocol

from pydantic import BaseModel, Field

from waygate_agent_sdk import BriefingResult, LiveDocumentRepository
from waygate_agent_sdk.models import (
    RetrievalQuery,
    RetrievalScope,
    RetrievedLiveDocument,
)
from waygate_core.schemas import DocumentStatus, DocumentType, Visibility
from waygate_storage.storage_base import StorageProvider


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
    def __init__(self, repository: BriefingRepository):
        self.repository = repository

    @classmethod
    def from_storage(cls, storage_provider: StorageProvider) -> "BriefingService":
        return cls(LiveDocumentRepository(storage_provider))

    def generate_briefing(self, request: GenerateBriefingRequest) -> BriefingResult:
        return self.repository.build_briefing(
            request.to_retrieval_query(),
            request.to_retrieval_scope(),
        )

    def preview_retrieval(
        self, request: GenerateBriefingRequest
    ) -> list[RetrievedLiveDocument]:
        return self.repository.retrieve(
            request.to_retrieval_query(),
            request.to_retrieval_scope(),
        )
