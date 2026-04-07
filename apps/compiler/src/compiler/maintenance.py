from __future__ import annotations

import json
from argparse import ArgumentParser
from collections.abc import Sequence
from datetime import datetime, timezone
from uuid import uuid4

from redis import Redis
from rq import Queue

from compiler.config import storage
from waygate_core.maintenance import (
    detect_maintenance_findings,
    persist_maintenance_findings,
)
from waygate_core.schemas import (
    AuditEvent,
    AuditEventType,
    MaintenanceFinding,
    RecompilationSignal,
)
from waygate_core.settings import get_runtime_settings


settings = get_runtime_settings()
redis_conn = Redis.from_url(settings.redis_url)
draft_queue = Queue(settings.draft_queue_name, connection=redis_conn)


def _build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Run a WayGate maintenance sweep")
    parser.add_argument(
        "--occurred-at",
        default=None,
        help="Override the maintenance finding timestamp",
    )
    parser.add_argument(
        "--enqueue-recompilation",
        action="store_true",
        help="Enqueue recompilation jobs for findings with embedded recompilation signals",
    )
    return parser


def _extract_recompilation_signal(
    finding: MaintenanceFinding,
) -> RecompilationSignal | None:
    payload = finding.payload.get("recompilation_signal")
    if not isinstance(payload, dict):
        return None
    return RecompilationSignal.model_validate(payload)


def _build_recompilation_state(signal: RecompilationSignal) -> dict:
    raw_documents_metadata = []
    raw_document_uris = []
    for doc_id in signal.lineage:
        raw_document = storage.get_raw_document_metadata(doc_id)
        raw_document_uri = storage.get_raw_document_uri(doc_id)
        if raw_document is None or raw_document_uri is None:
            raise ValueError(f"Missing raw document state for {doc_id}")

        raw_documents_metadata.append(raw_document.model_dump(mode="json"))
        raw_document_uris.append(raw_document_uri)

    live_metadata = storage.get_live_document_metadata(signal.live_document_uri)
    return {
        "state_version": "1",
        "trace_id": str(uuid4()),
        "enqueued_at": datetime.now(timezone.utc).isoformat(),
        "new_document_uris": raw_document_uris,
        "raw_documents_metadata": raw_documents_metadata,
        "target_topic": live_metadata.title,
        "document_type": str(live_metadata.document_type),
        "current_draft": None,
        "qa_feedback": None,
        "staging_uri": None,
        "revision_count": 0,
        "status": "pending_draft",
    }


def enqueue_recompilation_jobs(
    findings: list[MaintenanceFinding],
) -> list[dict[str, str]]:
    enqueued_jobs: list[dict[str, str]] = []
    for finding in findings:
        signal = _extract_recompilation_signal(finding)
        if signal is None:
            continue

        initial_state = _build_recompilation_state(signal)
        job = draft_queue.enqueue(
            "compiler.worker.execute_graph",
            initial_state,
            job_timeout="10m",
        )
        storage.write_audit_event(
            AuditEvent(
                event_type=AuditEventType.MAINTENANCE_RECOMPILATION_ENQUEUED,
                occurred_at=datetime.now(timezone.utc).isoformat(),
                trace_id=initial_state["trace_id"],
                document_ids=[signal.live_document_id, *signal.lineage],
                uris=[signal.live_document_uri, *initial_state["new_document_uris"]],
                payload={
                    "job_id": job.id,
                    "queue_name": settings.draft_queue_name,
                    "reason": signal.reason,
                    "live_document_id": signal.live_document_id,
                },
            )
        )
        enqueued_jobs.append(
            {
                "job_id": job.id,
                "live_document_id": signal.live_document_id,
                "live_document_uri": signal.live_document_uri,
            }
        )
    return enqueued_jobs


def run_maintenance_sweep(
    occurred_at: str | None = None,
) -> tuple[list[MaintenanceFinding], list[str]]:
    findings = detect_maintenance_findings(storage, occurred_at=occurred_at)
    finding_uris = persist_maintenance_findings(storage, findings)
    return findings, finding_uris


def main(argv: Sequence[str] | None = None) -> None:
    args = _build_parser().parse_args(list(argv) if argv is not None else None)
    findings, finding_uris = run_maintenance_sweep(occurred_at=args.occurred_at)
    enqueued_jobs = (
        enqueue_recompilation_jobs(findings) if args.enqueue_recompilation else []
    )
    summary = {
        "finding_count": len(findings),
        "finding_types": [str(finding.finding_type) for finding in findings],
        "finding_uris": finding_uris,
        "recompilation_job_ids": [entry["job_id"] for entry in enqueued_jobs],
    }
    print(json.dumps(summary))
