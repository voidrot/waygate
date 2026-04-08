from __future__ import annotations

from datetime import datetime, timedelta, timezone

from waygate_core.doc_helpers import build_provenance_hash
from waygate_core.schemas import (
    ContextErrorReport,
    DocumentType,
    MaintenanceFinding,
    MaintenanceFindingType,
    RecompilationSignal,
)
from waygate_storage.storage_base import StorageProvider


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _build_recompilation_signal(
    *,
    timestamp: str,
    live_document_uri: str,
    live_document_id: str,
    reason: str,
    lineage: list[str],
    payload: dict[str, object],
) -> RecompilationSignal | None:
    if not lineage:
        return None
    return RecompilationSignal(
        created_at=timestamp,
        live_document_uri=live_document_uri,
        live_document_id=live_document_id,
        reason=reason,
        lineage=lineage,
        payload=payload,
    )


def _build_context_error_recompilation_signal(
    report: ContextErrorReport,
) -> RecompilationSignal | None:
    if not report.lineage_ids:
        return None

    target_topic = report.query.strip() or report.message.strip() or "Context follow-up"
    return RecompilationSignal(
        created_at=report.occurred_at,
        reason="context_error",
        lineage=report.lineage_ids,
        target_topic=target_topic,
        document_type=DocumentType.CONCEPTS,
        payload={
            "message": report.message,
            "query": report.query,
            "tags": report.tags,
            "requested_visibilities": [
                str(item) for item in report.requested_visibilities
            ],
        },
    )


def detect_maintenance_findings(
    storage: StorageProvider,
    occurred_at: str | None = None,
    stale_after_hours: int | None = None,
) -> list[MaintenanceFinding]:
    timestamp = occurred_at or datetime.now(timezone.utc).isoformat()
    occurred_at_dt = _parse_timestamp(timestamp) or datetime.now(timezone.utc)
    stale_cutoff = (
        occurred_at_dt - timedelta(hours=stale_after_hours)
        if stale_after_hours is not None
        else None
    )
    findings: list[MaintenanceFinding] = []

    for uri in sorted(storage.list_live_documents()):
        metadata = storage.get_live_document_metadata(uri)
        if metadata.lineage:
            raw_documents = []
            missing_doc_ids: list[str] = []
            for doc_id in metadata.lineage:
                raw_document = storage.get_raw_document_metadata(doc_id)
                if raw_document is None:
                    missing_doc_ids.append(doc_id)
                    continue
                raw_documents.append(raw_document)

            if missing_doc_ids:
                findings.append(
                    MaintenanceFinding(
                        finding_type=MaintenanceFindingType.ORPHAN_LINEAGE,
                        occurred_at=timestamp,
                        live_document_uri=uri,
                        live_document_id=metadata.doc_id,
                        related_doc_ids=metadata.lineage,
                        uris=[uri],
                        payload={"missing_lineage_ids": missing_doc_ids},
                    )
                )
                continue

            expected_hash = build_provenance_hash(raw_documents)
            if (
                expected_hash
                and metadata.source_hash
                and expected_hash != metadata.source_hash
            ):
                signal = _build_recompilation_signal(
                    timestamp=timestamp,
                    live_document_uri=uri,
                    live_document_id=metadata.doc_id,
                    reason="hash_mismatch",
                    lineage=metadata.lineage,
                    payload={
                        "expected_source_hash": expected_hash,
                        "actual_source_hash": metadata.source_hash,
                    },
                )
                payload: dict[str, object] = {
                    "expected_source_hash": expected_hash,
                    "actual_source_hash": metadata.source_hash,
                }
                if signal is not None:
                    payload["recompilation_signal"] = signal.model_dump(mode="json")
                findings.append(
                    MaintenanceFinding(
                        finding_type=MaintenanceFindingType.HASH_MISMATCH,
                        occurred_at=timestamp,
                        live_document_uri=uri,
                        live_document_id=metadata.doc_id,
                        related_doc_ids=metadata.lineage,
                        uris=[uri],
                        payload=payload,
                    )
                )
                continue

        last_compiled = _parse_timestamp(metadata.last_compiled) or _parse_timestamp(
            metadata.last_updated
        )
        if (
            stale_cutoff is not None
            and last_compiled is not None
            and last_compiled <= stale_cutoff
        ):
            signal = _build_recompilation_signal(
                timestamp=timestamp,
                live_document_uri=uri,
                live_document_id=metadata.doc_id,
                reason="stale_compilation",
                lineage=metadata.lineage,
                payload={
                    "last_compiled": last_compiled.isoformat(),
                    "stale_after_hours": stale_after_hours,
                },
            )
            payload = {
                "last_compiled": last_compiled.isoformat(),
                "stale_after_hours": stale_after_hours,
            }
            if signal is not None:
                payload["recompilation_signal"] = signal.model_dump(mode="json")
            findings.append(
                MaintenanceFinding(
                    finding_type=MaintenanceFindingType.STALE_COMPILATION,
                    occurred_at=timestamp,
                    live_document_uri=uri,
                    live_document_id=metadata.doc_id,
                    related_doc_ids=metadata.lineage,
                    uris=[uri],
                    payload=payload,
                )
            )

    return findings


def persist_maintenance_findings(
    storage: StorageProvider,
    findings: list[MaintenanceFinding],
) -> list[str]:
    return [storage.write_maintenance_finding(finding) for finding in findings]


def record_context_error(
    storage: StorageProvider,
    report: ContextErrorReport,
) -> str:
    payload = report.model_dump(mode="json")
    signal = _build_context_error_recompilation_signal(report)
    if signal is not None:
        payload["recompilation_signal"] = signal.model_dump(mode="json")

    finding = MaintenanceFinding(
        finding_type=MaintenanceFindingType.CONTEXT_ERROR,
        occurred_at=report.occurred_at,
        trace_id=report.trace_id,
        related_doc_ids=report.lineage_ids,
        payload=payload,
    )
    return storage.write_maintenance_finding(finding)
