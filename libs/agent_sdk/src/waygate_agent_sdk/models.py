from pydantic import BaseModel, Field

from waygate_core.schemas import (
    DocumentStatus,
    DocumentType,
    FrontMatterDocument,
    Visibility,
)


class RetrievalScope(BaseModel):
    role: str | None = None
    allowed_visibilities: list[Visibility] = Field(
        default_factory=lambda: [Visibility.PUBLIC, Visibility.INTERNAL]
    )


class RetrievalQuery(BaseModel):
    query: str = ""
    max_documents: int = Field(default=5, ge=1)
    token_budget: int = Field(default=4000, ge=1)
    tags: list[str] = Field(default_factory=list)
    document_types: list[DocumentType | str] = Field(default_factory=list)
    statuses: list[DocumentStatus | str] = Field(
        default_factory=lambda: [DocumentStatus.LIVE, DocumentStatus.ACTIVE]
    )
    lineage_ids: list[str] = Field(default_factory=list)


class LoadedLiveDocument(BaseModel):
    uri: str
    metadata: FrontMatterDocument
    content: str
    token_estimate: int


class RetrievedLiveDocument(LoadedLiveDocument):
    score: float
    score_breakdown: dict[str, float] = Field(default_factory=dict)


class BriefingResult(BaseModel):
    documents: list[RetrievedLiveDocument] = Field(default_factory=list)
    content: str = ""
    total_token_estimate: int = 0
    truncated: bool = False
