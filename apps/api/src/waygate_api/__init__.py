import os

import uvicorn
from waygate_core.logging import get_logger
from waygate_core import bootstrap_app
from waygate_core.plugin import resolve_communication_client

__VERSION__ = "0.1.0"  # x-release-please-version

logger = get_logger(__name__)


def main() -> None:
    app_context = bootstrap_app()
    resolve_communication_client(
        app_context.plugins.communication,
        app_context.config.core.communication_plugin_name,
        allow_fallback=False,
    )

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    logger.info(f"Starting WayGate API Server on {host}:{port}")
    uvicorn.run("waygate_api.server:app", host=host, port=port)
