"""Public plugin contracts, DTOs, and registry helpers for WayGate."""

from .communication import (
    CommunicationClientPlugin,
    CommunicationClientResolutionError,
    CommunicationWorkerTransportPlugin,
    CommunicationWorkerTransportResolutionError,
    DispatchErrorKind,
    WorkflowTriggerRunner,
    WorkflowDispatchResult,
    WorkflowTriggerMessage,
    resolve_communication_client,
    resolve_communication_worker_transport,
)
from .cron import CronPlugin
from .hooks import PluginConfigRegistration, WayGatePluginSpec
from .llm import (
    LLMCommonOptions,
    LLMConfigurationError,
    LLMEmbeddingsProvider,
    LLMInvocationDiagnostics,
    LLMInvocationRequest,
    LLMOptionPolicy,
    LLMProviderCapabilities,
    LLMProviderPlugin,
    LLMReadinessProbe,
    LLMResolvedOptions,
    resolve_invocation_options,
)
from .registry import (
    WayGatePluginManager,
)
from .storage import StoragePlugin, StorageNamespace, StorageInvalidNamespaceError
from .webhook import WebhookPlugin, WebhookVerificationError

__all__ = [
    "CronPlugin",
    "CommunicationClientPlugin",
    "CommunicationClientResolutionError",
    "CommunicationWorkerTransportPlugin",
    "CommunicationWorkerTransportResolutionError",
    "DispatchErrorKind",
    "LLMCommonOptions",
    "LLMConfigurationError",
    "LLMEmbeddingsProvider",
    "LLMInvocationDiagnostics",
    "LLMInvocationRequest",
    "LLMOptionPolicy",
    "LLMProviderCapabilities",
    "LLMProviderPlugin",
    "LLMReadinessProbe",
    "LLMResolvedOptions",
    "StoragePlugin",
    "WorkflowTriggerRunner",
    "WorkflowDispatchResult",
    "WorkflowTriggerMessage",
    "resolve_communication_client",
    "resolve_communication_worker_transport",
    "WebhookPlugin",
    "PluginConfigRegistration",
    "WayGatePluginSpec",
    "WayGatePluginManager",
    "WebhookVerificationError",
    "StorageNamespace",
    "StorageInvalidNamespaceError",
    "resolve_invocation_options",
]
