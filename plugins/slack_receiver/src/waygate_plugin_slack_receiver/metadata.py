from typing import Literal

from pydantic import Field

from waygate_core.schemas import SourceMetadataBase


class SlackSourceMetadata(SourceMetadataBase):
    kind: Literal["slack"] = "slack"
    channel_id: str | None = None
    thread_ts: str | None = None
    participants: list[str] = Field(default_factory=list)
    semantic_type: str | None = None
    anchor_id: str | None = None
    reaction_ratio: float | None = None
