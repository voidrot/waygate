"""CLI entry point for the WayGate JetStream worker."""

from __future__ import annotations

import asyncio

from waygate_worker import run_nats_worker

__VERSION__ = "0.1.0"  # x-release-please-version


def main() -> None:
    """Start the JetStream worker process."""

    asyncio.run(run_nats_worker())
