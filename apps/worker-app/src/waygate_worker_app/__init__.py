"""CLI entry point for the transport-agnostic WayGate worker app."""

from __future__ import annotations

import asyncio

from waygate_worker import run_worker

__VERSION__ = "0.1.0"  # x-release-please-version


def main() -> None:
    """Start the shared worker app."""

    asyncio.run(run_worker())
