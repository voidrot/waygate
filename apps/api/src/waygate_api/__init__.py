"""Legacy CLI entrypoint for the WayGate API compatibility app."""

from os import getenv

import uvicorn

from waygate_core import bootstrap_app
from waygate_core.plugin import CommunicationClientResolutionError
from waygate_core.plugin import resolve_communication_client

__VERSION__ = "0.1.0"  # x-release-please-version


def main() -> None:
    """Preflight runtime configuration and start the legacy API server."""

    app_context = bootstrap_app()
    resolve_communication_client(
        app_context.plugins.communication,
        app_context.config.core.communication_plugin_name,
        allow_fallback=False,
    )

    host = getenv("HOST", "0.0.0.0")
    port = int(getenv("PORT", "8080"))
    uvicorn.run("waygate_api.server:app", host=host, port=port)


__all__ = [
    "CommunicationClientResolutionError",
    "__VERSION__",
    "bootstrap_app",
    "main",
    "uvicorn",
]
