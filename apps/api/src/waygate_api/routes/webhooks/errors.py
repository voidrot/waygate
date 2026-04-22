"""Compatibility shim for legacy API webhook dispatch error helpers."""

from waygate_webhooks.errors import map_dispatch_failure_to_http

__all__ = ["map_dispatch_failure_to_http"]
