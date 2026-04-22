"""CLI entrypoint for the unified WayGate web application."""

import uvicorn

from waygate_core import bootstrap_app
from waygate_core.plugin import CommunicationClientResolutionError
from waygate_core.plugin import resolve_communication_client

from .settings import WaygateWebRuntimeSettings

__VERSION__ = "0.1.0"  # x-release-please-version


def main() -> None:
    """Preflight runtime configuration and start the Uvicorn server."""

    app_context = bootstrap_app()
    web_settings = WaygateWebRuntimeSettings()

    resolve_communication_client(
        app_context.plugins.communication,
        app_context.config.core.communication_plugin_name,
        allow_fallback=False,
    )

    uvicorn.run(
        "waygate_web.server:app",
        host=web_settings.host,
        port=web_settings.port,
    )


__all__ = [
    "CommunicationClientResolutionError",
    "__VERSION__",
    "bootstrap_app",
    "main",
    "uvicorn",
]
