from pathlib import Path

from waygate_core.doc_helpers import generate_frontmatter
from waygate_core.maintenance import (
    detect_maintenance_findings,
    persist_maintenance_findings,
    record_context_error,
)
from waygate_core.schemas import (
    ContextErrorReport,
    FrontMatterDocument,
    MaintenanceFindingType,
    RawDocument,
    Visibility,
)
from waygate_plugin_local_storage.local_storage import LocalStorageProvider


def _storage(tmp_path: Path) -> LocalStorageProvider:
    provider = LocalStorageProvider.__new__(LocalStorageProvider)
    provider.base_dir = tmp_path
    provider.raw_dir = tmp_path / "raw"
    provider.live_dir = tmp_path / "live"
    provider.staging_dir = tmp_path / "staging"
    provider.meta_dir = tmp_path / "meta"
    provider.templates_dir = provider.meta_dir / "templates"
    provider.agents_dir = provider.meta_dir / "agents"
    provider.raw_dir.mkdir()
    provider.live_dir.mkdir()
    provider.staging_dir.mkdir()
    provider.templates_dir.mkdir(parents=True)
    provider.agents_dir.mkdir(parents=True)
    return provider


def test_detect_hash_mismatch_returns_recompilation_finding(tmp_path: Path) -> None:
    storage = _storage(tmp_path)
    raw = RawDocument.model_validate(
        {
            "doc_id": "raw-1",
            "source_type": "web",
            "source_id": "page-1",
            "timestamp": "2026-04-06T12:00:00+00:00",
            "content": "Body",
            "source_hash": "raw-hash",
            "visibility": Visibility.INTERNAL,
        }
    )
    storage.write_raw_documents([raw])
    live = (
        generate_frontmatter(
            FrontMatterDocument(
                doc_id="live-1",
                title="Live Doc",
                status="live",
                source_hash="outdated-hash",
                lineage=["raw-1"],
                last_compiled="2026-04-06T12:05:00+00:00",
            )
        )
        + "\nCompiled content"
    )
    storage.write_live_document_to_category("live-1", live, "concepts")

    findings = detect_maintenance_findings(
        storage, occurred_at="2026-04-06T13:00:00+00:00"
    )

    assert len(findings) == 1
    finding = findings[0]
    assert finding.finding_type == MaintenanceFindingType.HASH_MISMATCH
    assert finding.live_document_id == "live-1"
    assert finding.payload["actual_source_hash"] == "outdated-hash"
    assert finding.payload["recompilation_signal"]["reason"] == "hash_mismatch"


def test_detect_orphan_lineage_returns_finding(tmp_path: Path) -> None:
    storage = _storage(tmp_path)
    live = (
        generate_frontmatter(
            FrontMatterDocument(
                doc_id="live-2",
                title="Live Doc",
                status="live",
                lineage=["missing-raw"],
                last_compiled="2026-04-06T12:05:00+00:00",
            )
        )
        + "\nCompiled content"
    )
    storage.write_live_document_to_category("live-2", live, "concepts")

    findings = detect_maintenance_findings(
        storage, occurred_at="2026-04-06T13:00:00+00:00"
    )

    assert len(findings) == 1
    finding = findings[0]
    assert finding.finding_type == MaintenanceFindingType.ORPHAN_LINEAGE
    assert finding.payload["missing_lineage_ids"] == ["missing-raw"]


def test_persist_maintenance_findings_and_record_context_error(tmp_path: Path) -> None:
    storage = _storage(tmp_path)
    report = ContextErrorReport(
        occurred_at="2026-04-06T14:00:00+00:00",
        message="Briefing missing escalation policy",
        trace_id="trace-ctx-1",
        query="escalation policy",
        requested_visibilities=[Visibility.PUBLIC],
        lineage_ids=["raw-1"],
    )

    context_uri = record_context_error(storage, report)
    findings = detect_maintenance_findings(
        storage, occurred_at="2026-04-06T15:00:00+00:00"
    )
    persisted = persist_maintenance_findings(storage, findings)

    assert context_uri.startswith("meta/maintenance/")
    assert persisted == []
    saved = storage.read_maintenance_finding(context_uri)
    assert saved.finding_type == MaintenanceFindingType.CONTEXT_ERROR
    assert saved.trace_id == "trace-ctx-1"
