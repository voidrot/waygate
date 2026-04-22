"""Alembic metadata discovery for first-party libraries and installed packages."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass
from importlib import import_module
from importlib import metadata as importlib_metadata
from pathlib import Path
import tomllib

from sqlalchemy import MetaData

from .models import Base

MIGRATION_ENTRYPOINT_GROUP = "waygate.migrations"

MigrationMetadataFactory = Callable[[], MetaData | Iterable[MetaData]]


@dataclass(frozen=True)
class MigrationMetadataContributor:
    """Resolved migration metadata contributor."""

    name: str
    source: str
    factory: MigrationMetadataFactory


def waygate_migration_metadata() -> tuple[MetaData, ...]:
    """Return the core package metadata for migration discovery."""

    return (Base.metadata,)


def discover_migration_metadata(repo_root: Path | None = None) -> tuple[MetaData, ...]:
    """Collect target metadata from core, workspace members, and installed packages.

    Args:
        repo_root: Optional repository root used to inspect uv workspace members.

    Returns:
        An ordered tuple of SQLAlchemy metadata collections for Alembic.

    Raises:
        RuntimeError: If a contributor cannot be loaded or executed.
        TypeError: If a contributor returns an unsupported value.
    """

    contributors: list[MigrationMetadataContributor] = []
    seen_contributors: set[str] = set()

    if repo_root is not None:
        for contributor in _discover_workspace_contributors(repo_root):
            if contributor.name in seen_contributors:
                continue
            contributors.append(contributor)
            seen_contributors.add(contributor.name)

    for contributor in _discover_installed_contributors():
        if contributor.name in seen_contributors:
            continue
        contributors.append(contributor)
        seen_contributors.add(contributor.name)

    metadata_collections: list[MetaData] = []
    seen_metadata: set[int] = set()
    _append_metadata(metadata_collections, seen_metadata, Base.metadata)

    for contributor in contributors:
        try:
            result = contributor.factory()
        except Exception as exc:  # pragma: no cover - exercised via tests
            raise RuntimeError(
                "Migration metadata contributor "
                f"'{contributor.name}' from {contributor.source} failed"
            ) from exc

        for metadata in _iter_metadata(result, contributor=contributor):
            _append_metadata(metadata_collections, seen_metadata, metadata)

    return tuple(metadata_collections)


def _discover_workspace_contributors(
    repo_root: Path,
) -> tuple[MigrationMetadataContributor, ...]:
    """Load migration contributors declared by local uv workspace members."""

    root_pyproject = repo_root / "pyproject.toml"
    if not root_pyproject.exists():
        return ()

    with root_pyproject.open("rb") as file_handle:
        root_config = tomllib.load(file_handle)

    member_patterns = (
        root_config.get("tool", {})
        .get("uv", {})
        .get("workspace", {})
        .get("members", [])
    )

    contributors: list[MigrationMetadataContributor] = []
    for member_pattern in member_patterns:
        for member_path in sorted(repo_root.glob(member_pattern)):
            if not member_path.is_dir():
                continue
            contributors.extend(_load_workspace_member_contributors(member_path))

    return tuple(contributors)


def _load_workspace_member_contributors(
    member_path: Path,
) -> tuple[MigrationMetadataContributor, ...]:
    """Read a workspace member's migration contributors from its pyproject."""

    member_pyproject = member_path / "pyproject.toml"
    if not member_pyproject.exists():
        return ()

    with member_pyproject.open("rb") as file_handle:
        member_config = tomllib.load(file_handle)

    entry_points = (
        member_config.get("project", {})
        .get("entry-points", {})
        .get(MIGRATION_ENTRYPOINT_GROUP, {})
    )
    if not isinstance(entry_points, dict):
        return ()

    contributors: list[MigrationMetadataContributor] = []
    for name, target in entry_points.items():
        contributors.append(
            MigrationMetadataContributor(
                name=name,
                source=str(member_pyproject),
                factory=_load_factory(target, source=str(member_pyproject), name=name),
            )
        )

    return tuple(contributors)


def _discover_installed_contributors() -> tuple[MigrationMetadataContributor, ...]:
    """Load migration contributors from installed package entry points."""

    contributors: list[MigrationMetadataContributor] = []
    for entry_point in _select_entry_points(MIGRATION_ENTRYPOINT_GROUP):
        factory = entry_point.load()
        if not callable(factory):
            raise TypeError(
                "Migration metadata entry point "
                f"'{entry_point.name}' from {entry_point.value} must be callable"
            )

        contributors.append(
            MigrationMetadataContributor(
                name=entry_point.name,
                source=entry_point.value,
                factory=factory,
            )
        )

    return tuple(contributors)


def _select_entry_points(group: str) -> Sequence[importlib_metadata.EntryPoint]:
    """Return entry points for a group across Python versions."""

    entry_points = importlib_metadata.entry_points()
    if hasattr(entry_points, "select"):
        return tuple(entry_points.select(group=group))
    return tuple(entry_points.get(group, ()))


def _load_factory(
    target: str,
    *,
    source: str,
    name: str,
) -> MigrationMetadataFactory:
    """Resolve a ``module:attribute`` target into a callable factory."""

    try:
        module_name, attribute_name = target.split(":", maxsplit=1)
    except ValueError as exc:
        raise RuntimeError(
            f"Migration metadata entry point '{name}' in {source} must use module:attribute"
        ) from exc

    factory = getattr(import_module(module_name), attribute_name)
    if not callable(factory):
        raise TypeError(
            f"Migration metadata entry point '{name}' in {source} must resolve to a callable"
        )
    return factory


def _iter_metadata(
    result: MetaData | Iterable[MetaData],
    *,
    contributor: MigrationMetadataContributor,
) -> Iterator[MetaData]:
    """Yield metadata objects from a contributor result."""

    if isinstance(result, MetaData):
        yield result
        return

    if isinstance(result, Iterable) and not isinstance(result, (str, bytes)):
        for metadata in result:
            if not isinstance(metadata, MetaData):
                raise TypeError(
                    "Migration metadata contributor "
                    f"'{contributor.name}' from {contributor.source} must return MetaData objects"
                )
            yield metadata
        return

    raise TypeError(
        "Migration metadata contributor "
        f"'{contributor.name}' from {contributor.source} returned an unsupported value"
    )


def _append_metadata(
    metadata_collections: list[MetaData],
    seen_metadata: set[int],
    metadata: MetaData,
) -> None:
    """Append a metadata object once while preserving order."""

    metadata_id = id(metadata)
    if metadata_id in seen_metadata:
        return
    seen_metadata.add(metadata_id)
    metadata_collections.append(metadata)
