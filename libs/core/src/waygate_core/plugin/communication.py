"""Communication client and worker transport contracts for workflow triggers."""

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from enum import StrEnum

from pydantic import BaseModel, Field

WorkflowTriggerRunner = Callable[[dict[str, object] | str], dict[str, object]]


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


class CommunicationWorkerTransportResolutionError(RuntimeError):
    """Raised when a worker transport cannot be resolved from app context."""


def _resolve_named_plugin(
    plugins: Mapping[str, object],
    configured_name: str | None,
    *,
    allow_fallback: bool,
    missing_message: str,
    unset_message: str,
    unavailable_message: str,
) -> object:
    if not plugins:
        raise RuntimeError(missing_message)

    preferred_name = (configured_name or "").strip()
    if not preferred_name:
        raise RuntimeError(unset_message)

    selected = plugins.get(preferred_name)
    if selected is not None:
        return selected

    if allow_fallback:
        return plugins[next(iter(plugins))]

    available = ", ".join(sorted(plugins.keys()))
    raise RuntimeError(
        unavailable_message.format(
            preferred_name=preferred_name,
            available=available,
        )
    )


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

    try:
        return _resolve_named_plugin(
            clients,
            configured_name,
            allow_fallback=allow_fallback,
            missing_message="No communication plugins are installed",
            unset_message=(
                "WAYGATE_CORE__COMMUNICATION_PLUGIN_NAME must be set to an installed communication plugin"
            ),
            unavailable_message=(
                "Configured communication plugin '{preferred_name}' is unavailable. Installed communication plugins: {available}"
            ),
        )
    except RuntimeError as exc:
        raise CommunicationClientResolutionError(str(exc)) from exc


def resolve_communication_worker_transport(
    transports: Mapping[str, "CommunicationWorkerTransportPlugin"],
    configured_name: str | None,
    *,
    allow_fallback: bool = False,
) -> "CommunicationWorkerTransportPlugin":
    """Resolve a worker transport by configured communication plugin name."""

    try:
        return _resolve_named_plugin(
            transports,
            configured_name,
            allow_fallback=allow_fallback,
            missing_message="No communication worker transports are installed",
            unset_message=(
                "WAYGATE_CORE__COMMUNICATION_PLUGIN_NAME must be set to a communication plugin that also exposes a worker transport"
            ),
            unavailable_message=(
                "Configured communication plugin '{preferred_name}' does not expose a worker transport. Installed worker transports: {available}"
            ),
        )
    except RuntimeError as exc:
        raise CommunicationWorkerTransportResolutionError(str(exc)) from exc


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


class CommunicationWorkerTransportPlugin(ABC):
    """Base class for worker-side transports selected by communication plugin."""

    plugin_group: str = "waygate.plugins.communication"
    hook_name: str = "waygate_worker_transport_plugin"

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
    async def run(
        self,
        runner: WorkflowTriggerRunner,
        *,
        stop_event: asyncio.Event | None = None,
    ) -> None:
        """Start consuming workflow trigger messages for this transport."""

        raise NotImplementedError(
            "CommunicationWorkerTransportPlugin subclasses must implement run"
        )
