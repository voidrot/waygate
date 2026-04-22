"""Pydantic payload models for completed agent-session webhook uploads."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from waygate_core.schema.visibility import Visibility


class AgentSessionTokenUsage(BaseModel):
    """Optional token usage information for a session or message."""

    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class AgentSessionReference(BaseModel):
    """External or workspace reference associated with a session or message."""

    kind: str
    value: str
    title: str | None = None


class AgentSessionAttachment(BaseModel):
    """Attachment metadata associated with the session."""

    name: str
    kind: str | None = None
    uri: str | None = None
    mime_type: str | None = None


class AgentSessionWorkspace(BaseModel):
    """Workspace metadata captured by the upstream adapter."""

    workspace_name: str | None = None
    workspace_root: str | None = None
    active_file: str | None = None
    attached_paths: list[str] = Field(default_factory=list)


class AgentSessionRepository(BaseModel):
    """Repository metadata captured by the upstream adapter."""

    repository_name: str | None = None
    repository_url: str | None = None
    branch: str | None = None
    commit_sha: str | None = None
    dirty_worktree: bool | None = None


class AgentSessionToolCall(BaseModel):
    """Summary of a tool call that occurred during a session."""

    tool_name: str
    call_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = None
    status: str | None = None
    input_summary: str | None = None
    output_summary: str | None = None
    input_redacted: bool | None = None
    output_redacted: bool | None = None
    custom_metadata: dict[str, Any] = Field(default_factory=dict)


class AgentSessionToolResult(BaseModel):
    """Summary of a tool result captured in a transcript."""

    tool_name: str
    call_id: str | None = None
    status: str | None = None
    summary: str | None = None
    custom_metadata: dict[str, Any] = Field(default_factory=dict)


class AgentSessionMessage(BaseModel):
    """Single message within a completed agent-session transcript."""

    message_id: str
    turn_index: int = Field(ge=0)
    role: Literal["system", "user", "assistant", "tool", "participant"]
    created_at: datetime
    content: str
    model: str | None = None
    participant: str | None = None
    command: str | None = None
    tool_calls: list[AgentSessionToolCall] = Field(default_factory=list)
    tool_results: list[AgentSessionToolResult] = Field(default_factory=list)
    references: list[AgentSessionReference] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    token_usage: AgentSessionTokenUsage | None = None
    error: str | None = None
    custom_metadata: dict[str, Any] = Field(default_factory=dict)


class AgentSession(BaseModel):
    """Completed session envelope uploaded to the webhook."""

    session_id: str
    started_at: datetime
    completed_at: datetime
    title: str
    messages: list[AgentSessionMessage] = Field(min_length=1)
    thread_id: str | None = None
    subthread_id: str | None = None
    conversation_url: str | None = None
    summary: str | None = None
    topics: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    workspace: AgentSessionWorkspace | None = None
    repository: AgentSessionRepository | None = None
    token_usage: AgentSessionTokenUsage | None = None
    attachments: list[AgentSessionAttachment] = Field(default_factory=list)
    references: list[AgentSessionReference] = Field(default_factory=list)
    custom_metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_timestamps(self) -> "AgentSession":
        """Ensure the completed timestamp is not earlier than the start."""

        if self.completed_at < self.started_at:
            raise ValueError("completed_at must be greater than or equal to started_at")
        return self


class AgentSessionWebhookPayload(BaseModel):
    """Top-level payload accepted by the agent-session webhook route."""

    schema_version: str
    capture_adapter: str
    capture_adapter_version: str
    provider: str
    surface: str
    exported_at: datetime
    visibility: Visibility = Field(default=Visibility.INTERNAL)
    privacy_mode: str | None = None
    redaction_summary: str | None = None
    organization: str | None = None
    installation_id: str | None = None
    custom_metadata: dict[str, Any] = Field(default_factory=dict)
    session: AgentSession
