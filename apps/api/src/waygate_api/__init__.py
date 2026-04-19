import os

import uvicorn
from waygate_core.logging import get_logger
from waygate_core import bootstrap_app

__VERSION__ = "0.1.0"  # x-release-please-version

logger = get_logger(__name__)

bootstrap_app()


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    logger.info(f"Starting WayGate API Server on {host}:{port}")
    uvicorn.run("waygate_api.server:app", host=host, port=port)
