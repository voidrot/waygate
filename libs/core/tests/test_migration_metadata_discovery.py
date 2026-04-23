from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import MetaData, Table, Column, Integer

from waygate_core.database.discovery import (
    MIGRATION_ENTRYPOINT_GROUP,
    MigrationMetadataContributor,
    discover_migration_metadata,
)
from waygate_core.database.models import Base


def test_discover_migration_metadata_includes_core_base(monkeypatch) -> None:
    monkeypatch.setattr(
        "waygate_core.database.discovery._discover_workspace_contributors",
        lambda repo_root: (),
    )
    monkeypatch.setattr(
        "waygate_core.database.discovery._discover_installed_contributors",
        lambda: (),
    )

    metadata = discover_migration_metadata()

    assert metadata == (Base.metadata,)


def test_discover_migration_metadata_collects_workspace_and_installed_contributors(
    monkeypatch,
) -> None:
    workspace_metadata = MetaData()
    installed_metadata = MetaData()
    Table(
        "workspace_table", workspace_metadata, Column("id", Integer, primary_key=True)
    )
    Table(
        "installed_table", installed_metadata, Column("id", Integer, primary_key=True)
    )

    monkeypatch.setattr(
        "waygate_core.database.discovery._discover_workspace_contributors",
        lambda repo_root: (
            MigrationMetadataContributor(
                name="workspace-package",
                source="workspace",
                factory=lambda: (workspace_metadata,),
            ),
        ),
    )
    monkeypatch.setattr(
        "waygate_core.database.discovery._discover_installed_contributors",
        lambda: (
            MigrationMetadataContributor(
                name="third-party-plugin",
                source="installed",
                factory=lambda: installed_metadata,
            ),
        ),
    )

    metadata = discover_migration_metadata(repo_root=Path("/workspace"))

    assert metadata == (Base.metadata, workspace_metadata, installed_metadata)


def test_discover_migration_metadata_prefers_workspace_contributors_by_name(
    monkeypatch,
) -> None:
    workspace_metadata = MetaData()
    installed_metadata = MetaData()
    Table(
        "workspace_table", workspace_metadata, Column("id", Integer, primary_key=True)
    )
    Table(
        "installed_table", installed_metadata, Column("id", Integer, primary_key=True)
    )

    monkeypatch.setattr(
        "waygate_core.database.discovery._discover_workspace_contributors",
        lambda repo_root: (
            MigrationMetadataContributor(
                name="shared-package",
                source="workspace",
                factory=lambda: workspace_metadata,
            ),
        ),
    )
    monkeypatch.setattr(
        "waygate_core.database.discovery._discover_installed_contributors",
        lambda: (
            MigrationMetadataContributor(
                name="shared-package",
                source="installed",
                factory=lambda: installed_metadata,
            ),
        ),
    )

    metadata = discover_migration_metadata(repo_root=Path("/workspace"))

    assert metadata == (Base.metadata, workspace_metadata)


def test_discover_migration_metadata_rejects_invalid_contributor_results(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "waygate_core.database.discovery._discover_installed_contributors",
        lambda: (
            MigrationMetadataContributor(
                name="broken-package",
                source="installed",
                factory=lambda: object(),
            ),
        ),
    )

    try:
        discover_migration_metadata()
    except TypeError as exc:
        assert "broken-package" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("Expected TypeError for invalid migration metadata result")


def test_discover_workspace_contributors_reads_member_entry_points(
    tmp_path, monkeypatch
) -> None:
    repo_root = tmp_path / "repo"
    member_dir = repo_root / "libs" / "sample"
    package_src = member_dir / "src"
    package_src.mkdir(parents=True)

    (repo_root / "pyproject.toml").write_text(
        """
[tool.uv.workspace]
members = ["libs/*"]
""".strip()
    )
    (member_dir / "pyproject.toml").write_text(
        f"""
[project]
name = "sample-package"

[project.entry-points."{MIGRATION_ENTRYPOINT_GROUP}"]
sample-package = "sample_models:waygate_migration_metadata"
""".strip()
    )
    (package_src / "sample_models.py").write_text(
        """
from sqlalchemy import Column, Integer, MetaData, Table

metadata = MetaData()
Table("sample_table", metadata, Column("id", Integer, primary_key=True))

def waygate_migration_metadata():
    return metadata
""".strip()
    )

    monkeypatch.syspath_prepend(str(package_src))
    monkeypatch.setattr(
        "waygate_core.database.discovery._discover_installed_contributors",
        lambda: (),
    )
    sys.modules.pop("sample_models", None)

    metadata = discover_migration_metadata(repo_root=repo_root)

    assert len(metadata) == 2
    assert "sample_table" in metadata[1].tables
