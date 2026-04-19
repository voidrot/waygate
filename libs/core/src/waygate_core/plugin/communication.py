"""Communication client contracts and workflow-trigger transport DTOs."""

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Mapping

from pydantic import BaseModel, Field


class WorkflowTriggerMessage(BaseModel):
    """Transport-agnostic request sent to workflow workers."""

    event_type: str = Field(default="draft.ready")
    source: str = Field(default="waygate")
    document_paths: list[str] = Field(default_factory=list)
    idempotency_key: str | None = Field(default=None)
    metadata: dict[str, str] = Field(default_factory=dict)


class WorkflowDispatchResult(BaseModel):
    """Outcome of submitting a workflow trigger message to a transport."""

    accepted: bool = Field(default=False)
    transport_message_id: str | None = Field(default=None)
    detail: str | None = Field(default=None)
    error_kind: "DispatchErrorKind | None" = Field(default=None)


class DispatchErrorKind(StrEnum):
    """Classification for transport submission failures."""

    VALIDATION = "validation"
    CONFIG = "config"
    TRANSIENT = "transient"
    PERMANENT = "permanent"


class CommunicationClientResolutionError(RuntimeError):
    """Raised when a communication client cannot be resolved from app context."""


def resolve_communication_client(
    clients: Mapping[str, "CommunicationClientPlugin"],
    configured_name: str | None,
    *,
    allow_fallback: bool = False,
) -> "CommunicationClientPlugin":
    """Resolve a communication client by configured plugin name.

    Args:
        clients: Mapping of available client names to plugin instances.
        configured_name: The preferred configured client name.
        allow_fallback: Whether to fall back to the first installed client when
            the configured name is unavailable.

    Returns:
        The selected communication client plugin.

    Raises:
        CommunicationClientResolutionError: If no configured client can be
            resolved.
    """

    if not clients:
        raise CommunicationClientResolutionError(
            "No communication plugins are installed"
        )

    preferred_name = (configured_name or "").strip()
    if not preferred_name:
        raise CommunicationClientResolutionError(
            "WAYGATE_CORE__COMMUNICATION_PLUGIN_NAME must be set to an installed communication plugin"
        )

    selected = clients.get(preferred_name)
    if selected is not None:
        return selected

    if allow_fallback:
        return clients[next(iter(clients))]

    available = ", ".join(sorted(clients.keys()))
    raise CommunicationClientResolutionError(
        f"Configured communication plugin '{preferred_name}' is unavailable. Installed communication plugins: {available}"
    )


class CommunicationClientPlugin(ABC):
    """Base class for communication clients used to call worker runtimes."""

    plugin_group: str = "waygate.plugins.communication"
    hook_name: str = "waygate_communication_client_plugin"

    @property
    def name(self) -> str:
        return self.__class__.__name__

    @property
    def description(self) -> str:
        return "No description provided."

    @property
    def version(self) -> str:
        return "0.0.0"

    @abstractmethod
    async def submit_workflow_trigger(
        self,
        message: WorkflowTriggerMessage,
    ) -> WorkflowDispatchResult:
        """Submit a fire-and-forget workflow trigger request.

        Args:
            message: The trigger message to submit.

        Returns:
            The submission result from the underlying transport.
        """
        raise NotImplementedError(
            "CommunicationClientPlugin subclasses must implement submit_workflow_trigger"
        )
