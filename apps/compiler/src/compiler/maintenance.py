from __future__ import annotations

import json
from argparse import ArgumentParser
from collections.abc import Sequence
from datetime import datetime, timezone
from uuid import uuid4

from redis import Redis
from rq import Queue

from compiler.config import storage
from waygate_core.doc_helpers import generate_frontmatter, infer_initial_topic
from waygate_core.maintenance import (
    detect_maintenance_findings,
    persist_maintenance_findings,
)
from waygate_core.observability import configure_tracing, start_span
from waygate_core.schemas import (
    AuditEvent,
    AuditEventType,
    DocumentStatus,
    FrontMatterDocument,
    MaintenanceFinding,
    MaintenanceFindingType,
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
        "--stale-after-hours",
        type=int,
        default=None,
        help="Detect stale live documents whose last_compiled exceeds this age in hours",
    )
    parser.add_argument(
        "--enqueue-recompilation",
        action="store_true",
        help="Enqueue recompilation jobs for findings with embedded recompilation signals",
    )
    parser.add_argument(
        "--include-context-errors",
        action="store_true",
        help="Replay persisted context-error findings that carry embedded recompilation signals",
    )
    parser.add_argument(
        "--archive-orphans",
        action="store_true",
        help="Mark orphan-lineage live documents as archived and prepend a deprecation notice",
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
    raw_documents = []
    raw_documents_metadata = []
    raw_document_uris = []
    for doc_id in signal.lineage:
        raw_document = storage.get_raw_document_metadata(doc_id)
        raw_document_uri = storage.get_raw_document_uri(doc_id)
        if raw_document is None or raw_document_uri is None:
            raise ValueError(f"Missing raw document state for {doc_id}")

        raw_documents.append(raw_document)
        raw_documents_metadata.append(raw_document.model_dump(mode="json"))
        raw_document_uris.append(raw_document_uri)

    target_topic = signal.target_topic
    document_type = signal.document_type
    if signal.live_document_uri:
        live_metadata = storage.get_live_document_metadata(signal.live_document_uri)
        target_topic = target_topic or live_metadata.title
        document_type = document_type or str(live_metadata.document_type)

    if not target_topic:
        target_topic = infer_initial_topic(raw_documents)
    if not document_type:
        document_type = "concepts"

    return {
        "state_version": "1",
        "trace_id": str(uuid4()),
        "enqueued_at": datetime.now(timezone.utc).isoformat(),
        "new_document_uris": raw_document_uris,
        "raw_documents_metadata": raw_documents_metadata,
        "target_topic": target_topic,
        "document_type": str(document_type),
        "current_draft": None,
        "qa_feedback": None,
        "staging_uri": None,
        "revision_count": 0,
        "status": "pending_draft",
    }


def load_persisted_context_error_findings() -> list[MaintenanceFinding]:
    with start_span(
        "compiler.maintenance.load_context_error_findings",
        tracer_name=__name__,
    ) as span:
        findings: list[MaintenanceFinding] = []
        for uri in storage.list_maintenance_findings():
            finding = storage.read_maintenance_finding(uri)
            if finding.finding_type != MaintenanceFindingType.CONTEXT_ERROR:
                continue
            if _extract_recompilation_signal(finding) is None:
                continue
            findings.append(finding)
        span.set_attribute("waygate.finding_count", len(findings))
        return findings


def _extract_live_document_body(content: str) -> str:
    if not content.startswith("---\n"):
        return content.lstrip("\n")

    separator = "\n---\n"
    end = content.find(separator, 4)
    if end == -1:
        return content.lstrip("\n")
    return content[end + len(separator) :].lstrip("\n")


def _build_orphan_archive_notice(
    finding: MaintenanceFinding,
    occurred_at: str,
) -> str:
    missing_doc_ids = finding.payload.get("missing_lineage_ids", [])
    missing = (
        ", ".join(missing_doc_ids) if isinstance(missing_doc_ids, list) else "unknown"
    )
    return (
        f"> [!WARNING]\n"
        f"> Archived during maintenance sweep at {occurred_at} because raw lineage sources are missing.\n"
        f"> Missing lineage IDs: {missing}"
    )


def archive_orphan_documents(
    findings: list[MaintenanceFinding],
    occurred_at: str | None = None,
) -> list[str]:
    timestamp = occurred_at or datetime.now(timezone.utc).isoformat()
    with start_span(
        "compiler.maintenance.archive_orphans",
        tracer_name=__name__,
        attributes={
            "waygate.finding_count": len(findings),
        },
    ) as span:
        archived_uris: list[str] = []

        for finding in findings:
            if finding.finding_type != MaintenanceFindingType.ORPHAN_LINEAGE:
                continue
            if not finding.live_document_uri:
                continue

            metadata = storage.get_live_document_metadata(finding.live_document_uri)
            body = _extract_live_document_body(
                storage.read_live_document(finding.live_document_uri)
            )
            notice = _build_orphan_archive_notice(finding, timestamp)
            archived_body = (
                body
                if body.startswith(notice)
                else (notice if not body else f"{notice}\n\n{body}")
            )
            updated_metadata = FrontMatterDocument.model_validate(
                {
                    **metadata.model_dump(mode="json"),
                    "status": DocumentStatus.ARCHIVED,
                    "last_updated": timestamp,
                }
            )
            updated_content = (
                f"{generate_frontmatter(updated_metadata)}\n{archived_body}"
            )
            storage.update_live_document(finding.live_document_uri, updated_content)
            storage.write_audit_event(
                AuditEvent(
                    event_type=AuditEventType.MAINTENANCE_ORPHAN_ARCHIVED,
                    occurred_at=timestamp,
                    trace_id=finding.trace_id,
                    document_ids=[metadata.doc_id, *finding.related_doc_ids],
                    uris=[finding.live_document_uri],
                    payload={
                        "missing_lineage_ids": finding.payload.get(
                            "missing_lineage_ids", []
                        ),
                        "live_document_id": metadata.doc_id,
                    },
                )
            )
            archived_uris.append(finding.live_document_uri)

        span.set_attribute("waygate.archived_count", len(archived_uris))
        return archived_uris


def enqueue_recompilation_jobs(
    findings: list[MaintenanceFinding],
) -> list[dict[str, str | None]]:
    with start_span(
        "compiler.maintenance.enqueue_recompilation",
        tracer_name=__name__,
        attributes={
            "waygate.finding_count": len(findings),
            "waygate.queue_name": settings.draft_queue_name,
        },
    ) as span:
        enqueued_jobs: list[dict[str, str | None]] = []
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
                    document_ids=[
                        *([signal.live_document_id] if signal.live_document_id else []),
                        *signal.lineage,
                    ],
                    uris=[
                        *(
                            [signal.live_document_uri]
                            if signal.live_document_uri
                            else []
                        ),
                        *initial_state["new_document_uris"],
                    ],
                    payload={
                        "job_id": job.id,
                        "queue_name": settings.draft_queue_name,
                        "reason": signal.reason,
                        "live_document_id": signal.live_document_id,
                        "target_topic": initial_state["target_topic"],
                    },
                )
            )
            enqueued_jobs.append(
                {
                    "job_id": job.id,
                    "live_document_id": signal.live_document_id,
                    "live_document_uri": signal.live_document_uri,
                    "target_topic": initial_state["target_topic"],
                }
            )
        span.set_attribute("waygate.job_count", len(enqueued_jobs))
        return enqueued_jobs


def run_maintenance_sweep(
    occurred_at: str | None = None,
    stale_after_hours: int | None = None,
) -> tuple[list[MaintenanceFinding], list[str]]:
    with start_span(
        "compiler.maintenance.detect_and_persist",
        tracer_name=__name__,
        attributes={
            "waygate.stale_after_hours": stale_after_hours,
        },
    ) as span:
        findings = detect_maintenance_findings(
            storage,
            occurred_at=occurred_at,
            stale_after_hours=stale_after_hours,
        )
        finding_uris = persist_maintenance_findings(storage, findings)
        span.set_attribute("waygate.finding_count", len(findings))
        return findings, finding_uris


def main(argv: Sequence[str] | None = None) -> None:
    args = _build_parser().parse_args(list(argv) if argv is not None else None)
    configure_tracing("waygate-compiler-maintenance")
    with start_span(
        "compiler.maintenance.main",
        tracer_name=__name__,
        attributes={
            "waygate.stale_after_hours": args.stale_after_hours,
            "waygate.enqueue_recompilation": args.enqueue_recompilation,
            "waygate.include_context_errors": args.include_context_errors,
            "waygate.archive_orphans": args.archive_orphans,
        },
    ) as span:
        findings, finding_uris = run_maintenance_sweep(
            occurred_at=args.occurred_at,
            stale_after_hours=args.stale_after_hours,
        )
        replayed_context_errors = (
            load_persisted_context_error_findings()
            if args.include_context_errors
            else []
        )
        enqueued_jobs = (
            enqueue_recompilation_jobs([*findings, *replayed_context_errors])
            if args.enqueue_recompilation
            else []
        )
        archived_orphan_uris = (
            archive_orphan_documents(findings, occurred_at=args.occurred_at)
            if args.archive_orphans
            else []
        )
        summary = {
            "finding_count": len(findings),
            "finding_types": [str(finding.finding_type) for finding in findings],
            "finding_uris": finding_uris,
            "recompilation_job_ids": [entry["job_id"] for entry in enqueued_jobs],
            "replayed_context_error_count": len(replayed_context_errors),
            "archived_orphan_uris": archived_orphan_uris,
        }
        span.set_attribute("waygate.finding_count", len(findings))
        span.set_attribute(
            "waygate.replayed_context_error_count", len(replayed_context_errors)
        )
        span.set_attribute("waygate.job_count", len(enqueued_jobs))
        span.set_attribute("waygate.archived_count", len(archived_orphan_uris))
        print(json.dumps(summary))
