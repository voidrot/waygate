"""Compatibility shims for the legacy API webhook router module."""

from waygate_webhooks.handlers import create_webhook_router
from waygate_webhooks.openapi import build_webhook_openapi_extra

webhook_router = create_webhook_router(prefix="/webhooks")
_build_openapi_extra = build_webhook_openapi_extra

__all__ = ["_build_openapi_extra", "webhook_router"]
