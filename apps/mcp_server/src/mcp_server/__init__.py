from __future__ import annotations

from importlib import import_module
from typing import Any

from mcp_server.main import main
from mcp_server.service import BriefingService, GenerateBriefingRequest


def create_http_app(*args: Any, **kwargs: Any):
    from mcp_server.server import create_http_app as _create_http_app

    return _create_http_app(*args, **kwargs)


def create_mcp_server(*args: Any, **kwargs: Any):
    from mcp_server.server import create_mcp_server as _create_mcp_server

    return _create_mcp_server(*args, **kwargs)


def __getattr__(name: str) -> Any:
    if name in {"app", "mcp"}:
        module = import_module("mcp_server.server")
        return getattr(module, name)
    raise AttributeError(f"module 'mcp_server' has no attribute {name!r}")


__all__ = [
    "BriefingService",
    "GenerateBriefingRequest",
    "main",
    "app",
    "create_http_app",
    "create_mcp_server",
    "mcp",
]
