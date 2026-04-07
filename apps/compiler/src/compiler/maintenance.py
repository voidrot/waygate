from __future__ import annotations

import json
from argparse import ArgumentParser
from collections.abc import Sequence

from compiler.config import storage
from waygate_core.maintenance import (
    detect_maintenance_findings,
    persist_maintenance_findings,
)
from waygate_core.schemas import MaintenanceFinding


def _build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Run a WayGate maintenance sweep")
    parser.add_argument(
        "--occurred-at",
        default=None,
        help="Override the maintenance finding timestamp",
    )
    return parser


def run_maintenance_sweep(
    occurred_at: str | None = None,
) -> tuple[list[MaintenanceFinding], list[str]]:
    findings = detect_maintenance_findings(storage, occurred_at=occurred_at)
    finding_uris = persist_maintenance_findings(storage, findings)
    return findings, finding_uris


def main(argv: Sequence[str] | None = None) -> None:
    args = _build_parser().parse_args(list(argv) if argv is not None else None)
    findings, finding_uris = run_maintenance_sweep(occurred_at=args.occurred_at)
    summary = {
        "finding_count": len(findings),
        "finding_types": [str(finding.finding_type) for finding in findings],
        "finding_uris": finding_uris,
    }
    print(json.dumps(summary))
