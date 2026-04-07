import json

from compiler import maintenance as maintenance_module
from waygate_core.schemas import MaintenanceFinding, MaintenanceFindingType


def test_run_maintenance_sweep_detects_and_persists(monkeypatch) -> None:
    finding = MaintenanceFinding(
        finding_type=MaintenanceFindingType.HASH_MISMATCH,
        occurred_at="2026-04-07T00:00:00+00:00",
        live_document_id="live-1",
    )

    monkeypatch.setattr(
        maintenance_module,
        "detect_maintenance_findings",
        lambda storage, occurred_at=None: [finding],
    )
    monkeypatch.setattr(
        maintenance_module,
        "persist_maintenance_findings",
        lambda storage, findings: ["meta/maintenance/finding-1"],
    )

    findings, uris = maintenance_module.run_maintenance_sweep(
        occurred_at="2026-04-07T00:00:00+00:00"
    )

    assert findings == [finding]
    assert uris == ["meta/maintenance/finding-1"]


def test_main_outputs_json_summary(monkeypatch, capsys) -> None:
    finding = MaintenanceFinding(
        finding_type=MaintenanceFindingType.ORPHAN_LINEAGE,
        occurred_at="2026-04-07T00:00:00+00:00",
        live_document_id="live-2",
    )
    monkeypatch.setattr(
        maintenance_module,
        "run_maintenance_sweep",
        lambda occurred_at=None: ([finding], ["meta/maintenance/finding-2"]),
    )

    maintenance_module.main(["--occurred-at", "2026-04-07T00:00:00+00:00"])

    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "finding_count": 1,
        "finding_types": ["orphan_lineage"],
        "finding_uris": ["meta/maintenance/finding-2"],
    }
