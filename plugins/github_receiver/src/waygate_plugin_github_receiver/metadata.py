from typing import Literal

from pydantic import Field

from waygate_core.schemas import SourceMetadataBase


class GitHubSourceMetadata(SourceMetadataBase):
    kind: Literal["github"] = "github"
    repo_name: str | None = None
    branch: str | None = None
    commit_sha: str | None = None
    owner: str | None = None
    tech_stack: list[str] = Field(default_factory=list)
    token_count: int | None = None
