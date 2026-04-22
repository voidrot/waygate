"""Mountable FastAPI webhook ingress for WayGate."""

from .app import create_webhook_app
from .dispatch import send_draft_message, send_workflow_message
from .errors import map_dispatch_failure_to_http
from .handlers import create_webhook_router
from .openapi import build_webhook_openapi_extra, merge_mounted_webhook_openapi

__VERSION__ = "0.1.0"  # x-release-please-version

__all__ = [
    "__VERSION__",
    "build_webhook_openapi_extra",
    "create_webhook_app",
    "create_webhook_router",
    "map_dispatch_failure_to_http",
    "merge_mounted_webhook_openapi",
    "send_draft_message",
    "send_workflow_message",
]
