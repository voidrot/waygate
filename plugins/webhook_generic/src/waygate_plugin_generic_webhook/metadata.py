from typing import Literal

from pydantic import Field

from waygate_core.schemas import SourceMetadataBase


class WebSourceMetadata(SourceMetadataBase):
    kind: Literal["web"] = "web"
    author: str | None = None
    clipped_at: str | None = None
    domain: str | None = None
    local_assets: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
