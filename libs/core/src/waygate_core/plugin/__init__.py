"""Public plugin contracts, DTOs, and registry helpers for WayGate."""

from .communication import (
    CommunicationClientPlugin,
    CommunicationClientResolutionError,
    DispatchErrorKind,
    WorkflowDispatchResult,
    WorkflowTriggerMessage,
    resolve_communication_client,
)
from .cron import CronPlugin
from .hooks import PluginConfigRegistration, WayGatePluginSpec
from .llm import (
    LLMCommonOptions,
    LLMConfigurationError,
    LLMInvocationDiagnostics,
    LLMInvocationRequest,
    LLMOptionPolicy,
    LLMProviderCapabilities,
    LLMProviderPlugin,
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
    "DispatchErrorKind",
    "LLMCommonOptions",
    "LLMConfigurationError",
    "LLMInvocationDiagnostics",
    "LLMInvocationRequest",
    "LLMOptionPolicy",
    "LLMProviderCapabilities",
    "LLMProviderPlugin",
    "LLMResolvedOptions",
    "StoragePlugin",
    "WorkflowDispatchResult",
    "WorkflowTriggerMessage",
    "resolve_communication_client",
    "WebhookPlugin",
    "PluginConfigRegistration",
    "WayGatePluginSpec",
    "WayGatePluginManager",
    "WebhookVerificationError",
    "StorageNamespace",
    "StorageInvalidNamespaceError",
    "resolve_invocation_options",
]
