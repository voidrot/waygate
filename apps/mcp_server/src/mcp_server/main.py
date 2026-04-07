from __future__ import annotations

from argparse import ArgumentParser
from collections.abc import Sequence

import uvicorn

from waygate_core.settings import reload_runtime_settings


def _build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Run the WayGate MCP server")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    args = _build_parser().parse_args(list(argv) if argv is not None else None)
    settings = reload_runtime_settings()
    uvicorn.run(
        "mcp_server.server:app",
        host=settings.mcp_server_host,
        port=settings.mcp_server_port,
        reload=args.reload,
    )
