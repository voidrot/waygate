from __future__ import annotations

from datetime import datetime, timezone

from waygate_core.doc_helpers import build_provenance_hash
from waygate_core.schemas import (
    ContextErrorReport,
    MaintenanceFinding,
    MaintenanceFindingType,
    RecompilationSignal,
)
from waygate_storage.storage_base import StorageProvider


def detect_maintenance_findings(
    storage: StorageProvider,
    occurred_at: str | None = None,
) -> list[MaintenanceFinding]:
    timestamp = occurred_at or datetime.now(timezone.utc).isoformat()
    findings: list[MaintenanceFinding] = []

    for uri in sorted(storage.list_live_documents()):
        metadata = storage.get_live_document_metadata(uri)
        if not metadata.lineage:
            continue

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
            signal = RecompilationSignal(
                created_at=timestamp,
                live_document_uri=uri,
                live_document_id=metadata.doc_id,
                reason="hash_mismatch",
                lineage=metadata.lineage,
                payload={
                    "expected_source_hash": expected_hash,
                    "actual_source_hash": metadata.source_hash,
                },
            )
            findings.append(
                MaintenanceFinding(
                    finding_type=MaintenanceFindingType.HASH_MISMATCH,
                    occurred_at=timestamp,
                    live_document_uri=uri,
                    live_document_id=metadata.doc_id,
                    related_doc_ids=metadata.lineage,
                    uris=[uri],
                    payload={
                        "expected_source_hash": expected_hash,
                        "actual_source_hash": metadata.source_hash,
                        "recompilation_signal": signal.model_dump(mode="json"),
                    },
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
    finding = MaintenanceFinding(
        finding_type=MaintenanceFindingType.CONTEXT_ERROR,
        occurred_at=report.occurred_at,
        trace_id=report.trace_id,
        related_doc_ids=report.lineage_ids,
        payload=report.model_dump(mode="json"),
    )
    return storage.write_maintenance_finding(finding)
