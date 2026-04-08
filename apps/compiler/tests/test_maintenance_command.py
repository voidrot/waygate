import json
from datetime import datetime, timezone

from compiler import maintenance as maintenance_module
from waygate_core.doc_helpers import generate_frontmatter
from waygate_core.plugin_base import RawDocument
from waygate_core.schemas import (
    AuditEventType,
    FrontMatterDocument,
    MaintenanceFinding,
    MaintenanceFindingType,
)


def test_run_maintenance_sweep_detects_and_persists(monkeypatch) -> None:
    finding = MaintenanceFinding(
        finding_type=MaintenanceFindingType.HASH_MISMATCH,
        occurred_at="2026-04-07T00:00:00+00:00",
        live_document_id="live-1",
    )
    captured = {}

    monkeypatch.setattr(
        maintenance_module,
        "detect_maintenance_findings",
        lambda storage, occurred_at=None, stale_after_hours=None: (
            captured.update(
                {
                    "occurred_at": occurred_at,
                    "stale_after_hours": stale_after_hours,
                }
            )
            or [finding]
        ),
    )
    monkeypatch.setattr(
        maintenance_module,
        "persist_maintenance_findings",
        lambda storage, findings: ["meta/maintenance/finding-1"],
    )

    findings, uris = maintenance_module.run_maintenance_sweep(
        occurred_at="2026-04-07T00:00:00+00:00",
        stale_after_hours=24,
    )

    assert findings == [finding]
    assert uris == ["meta/maintenance/finding-1"]
    assert captured == {
        "occurred_at": "2026-04-07T00:00:00+00:00",
        "stale_after_hours": 24,
    }


def test_main_outputs_json_summary(monkeypatch, capsys) -> None:
    finding = MaintenanceFinding(
        finding_type=MaintenanceFindingType.ORPHAN_LINEAGE,
        occurred_at="2026-04-07T00:00:00+00:00",
        live_document_id="live-2",
    )
    monkeypatch.setattr(
        maintenance_module,
        "run_maintenance_sweep",
        lambda occurred_at=None, stale_after_hours=None: (
            [finding],
            ["meta/maintenance/finding-2"],
        ),
    )

    maintenance_module.main(
        [
            "--occurred-at",
            "2026-04-07T00:00:00+00:00",
            "--stale-after-hours",
            "24",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "finding_count": 1,
        "finding_types": ["orphan_lineage"],
        "finding_uris": ["meta/maintenance/finding-2"],
        "recompilation_job_ids": [],
        "replayed_context_error_count": 0,
        "archived_orphan_uris": [],
    }


class _FakeStorage:
    def __init__(self) -> None:
        self.audit_events = []
        self.maintenance_findings = {}
        self.updated_live_documents = {}
        self.live_documents = {
            "file:///tmp/live/concepts/live-1.md": (
                generate_frontmatter(
                    FrontMatterDocument(
                        doc_id="live-1",
                        title="Recovered Topic",
                        document_type="concepts",
                        last_compiled="2026-04-07T00:00:00+00:00",
                        status="live",
                    )
                )
                + "\nExisting content"
            )
        }

    def get_raw_document_metadata(self, doc_id: str):
        return RawDocument(
            doc_id=doc_id,
            source_type="github",
            source_id=f"issue/{doc_id}",
            timestamp=datetime(2026, 4, 7, tzinfo=timezone.utc),
            content="hello",
        )

    def get_raw_document_uri(self, doc_id: str) -> str:
        return f"file:///tmp/raw/{doc_id}.md"

    def get_live_document_metadata(self, _uri: str):
        return FrontMatterDocument(
            doc_id="live-1",
            title="Recovered Topic",
            document_type="concepts",
            last_compiled="2026-04-07T00:00:00+00:00",
            status="live",
        )

    def read_live_document(self, uri: str) -> str:
        return self.live_documents[uri]

    def update_live_document(self, uri: str, content: str) -> str:
        self.updated_live_documents[uri] = content
        self.live_documents[uri] = content
        return uri

    def list_maintenance_findings(self) -> list[str]:
        return list(self.maintenance_findings)

    def read_maintenance_finding(self, uri: str):
        return self.maintenance_findings[uri]

    def write_audit_event(self, event) -> str:
        self.audit_events.append(event)
        return f"meta/audit/{event.event_id}"


class _FakeJob:
    def __init__(self, job_id: str) -> None:
        self.id = job_id


class _FakeQueue:
    def __init__(self) -> None:
        self.calls = []

    def enqueue(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return _FakeJob("job-recompile-1")


def test_enqueue_recompilation_jobs_uses_embedded_signal(monkeypatch) -> None:
    fake_storage = _FakeStorage()
    fake_queue = _FakeQueue()
    finding = MaintenanceFinding(
        finding_type=MaintenanceFindingType.HASH_MISMATCH,
        occurred_at="2026-04-07T00:00:00+00:00",
        live_document_id="live-1",
        live_document_uri="file:///tmp/live/concepts/live-1.md",
        payload={
            "recompilation_signal": {
                "signal_id": "signal-1",
                "created_at": "2026-04-07T00:00:00+00:00",
                "live_document_uri": "file:///tmp/live/concepts/live-1.md",
                "live_document_id": "live-1",
                "reason": "hash_mismatch",
                "lineage": ["raw-1"],
                "payload": {},
            }
        },
    )

    monkeypatch.setattr(maintenance_module, "storage", fake_storage)
    monkeypatch.setattr(maintenance_module, "draft_queue", fake_queue)

    jobs = maintenance_module.enqueue_recompilation_jobs([finding])

    assert jobs == [
        {
            "job_id": "job-recompile-1",
            "live_document_id": "live-1",
            "live_document_uri": "file:///tmp/live/concepts/live-1.md",
            "target_topic": "Recovered Topic",
        }
    ]
    assert fake_queue.calls
    args, kwargs = fake_queue.calls[0]
    assert args[0] == "compiler.worker.execute_graph"
    assert args[1]["target_topic"] == "Recovered Topic"
    assert args[1]["new_document_uris"] == ["file:///tmp/raw/raw-1.md"]
    assert len(fake_storage.audit_events) == 1
    assert (
        fake_storage.audit_events[0].event_type
        == AuditEventType.MAINTENANCE_RECOMPILATION_ENQUEUED
    )
    assert kwargs["job_timeout"] == "10m"


def test_enqueue_recompilation_jobs_supports_stale_compilation(monkeypatch) -> None:
    fake_storage = _FakeStorage()
    fake_queue = _FakeQueue()
    finding = MaintenanceFinding(
        finding_type=MaintenanceFindingType.STALE_COMPILATION,
        occurred_at="2026-04-08T00:00:00+00:00",
        live_document_id="live-1",
        live_document_uri="file:///tmp/live/concepts/live-1.md",
        payload={
            "recompilation_signal": {
                "signal_id": "signal-stale-1",
                "created_at": "2026-04-08T00:00:00+00:00",
                "live_document_uri": "file:///tmp/live/concepts/live-1.md",
                "live_document_id": "live-1",
                "reason": "stale_compilation",
                "lineage": ["raw-1"],
                "payload": {"stale_after_hours": 24},
            }
        },
    )

    monkeypatch.setattr(maintenance_module, "storage", fake_storage)
    monkeypatch.setattr(maintenance_module, "draft_queue", fake_queue)

    jobs = maintenance_module.enqueue_recompilation_jobs([finding])

    assert jobs[0]["job_id"] == "job-recompile-1"
    assert fake_storage.audit_events[0].payload["reason"] == "stale_compilation"


def test_enqueue_recompilation_jobs_supports_context_errors(monkeypatch) -> None:
    fake_storage = _FakeStorage()
    fake_queue = _FakeQueue()
    finding = MaintenanceFinding(
        finding_type=MaintenanceFindingType.CONTEXT_ERROR,
        occurred_at="2026-04-08T00:00:00+00:00",
        related_doc_ids=["raw-1"],
        payload={
            "recompilation_signal": {
                "signal_id": "signal-context-1",
                "created_at": "2026-04-08T00:00:00+00:00",
                "reason": "context_error",
                "lineage": ["raw-1"],
                "target_topic": "database failover escalation policy",
                "document_type": "concepts",
                "payload": {"message": "Missing policy"},
            }
        },
    )

    monkeypatch.setattr(maintenance_module, "storage", fake_storage)
    monkeypatch.setattr(maintenance_module, "draft_queue", fake_queue)

    jobs = maintenance_module.enqueue_recompilation_jobs([finding])

    assert jobs[0]["job_id"] == "job-recompile-1"
    args, _kwargs = fake_queue.calls[0]
    assert args[1]["target_topic"] == "database failover escalation policy"
    assert fake_storage.audit_events[0].payload["reason"] == "context_error"


def test_load_persisted_context_error_findings_filters_signal_backed_findings(
    monkeypatch,
) -> None:
    fake_storage = _FakeStorage()
    fake_storage.maintenance_findings = {
        "meta/maintenance/context-1": MaintenanceFinding(
            finding_type=MaintenanceFindingType.CONTEXT_ERROR,
            occurred_at="2026-04-08T00:00:00+00:00",
            payload={
                "recompilation_signal": {
                    "signal_id": "signal-context-1",
                    "created_at": "2026-04-08T00:00:00+00:00",
                    "reason": "context_error",
                    "lineage": ["raw-1"],
                    "target_topic": "database failover escalation policy",
                    "document_type": "concepts",
                    "payload": {},
                }
            },
        ),
        "meta/maintenance/context-2": MaintenanceFinding(
            finding_type=MaintenanceFindingType.CONTEXT_ERROR,
            occurred_at="2026-04-08T00:00:00+00:00",
            payload={},
        ),
    }

    monkeypatch.setattr(maintenance_module, "storage", fake_storage)

    findings = maintenance_module.load_persisted_context_error_findings()

    assert [finding.finding_type for finding in findings] == [
        MaintenanceFindingType.CONTEXT_ERROR
    ]


def test_archive_orphan_documents_marks_live_doc_archived(monkeypatch) -> None:
    fake_storage = _FakeStorage()
    finding = MaintenanceFinding(
        finding_type=MaintenanceFindingType.ORPHAN_LINEAGE,
        occurred_at="2026-04-08T00:00:00+00:00",
        live_document_id="live-1",
        live_document_uri="file:///tmp/live/concepts/live-1.md",
        related_doc_ids=["missing-raw"],
        payload={"missing_lineage_ids": ["missing-raw"]},
    )

    monkeypatch.setattr(maintenance_module, "storage", fake_storage)

    archived_uris = maintenance_module.archive_orphan_documents(
        [finding],
        occurred_at="2026-04-08T00:00:00+00:00",
    )

    assert archived_uris == ["file:///tmp/live/concepts/live-1.md"]
    updated_content = fake_storage.updated_live_documents[archived_uris[0]]
    assert "status: archived" in updated_content
    assert "Missing lineage IDs: missing-raw" in updated_content
    assert (
        fake_storage.audit_events[0].event_type
        == AuditEventType.MAINTENANCE_ORPHAN_ARCHIVED
    )
