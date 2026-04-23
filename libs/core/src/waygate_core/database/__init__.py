"""Database metadata helpers used by Alembic and ORM-owning packages."""

from .discovery import (
    MIGRATION_ENTRYPOINT_GROUP,
    discover_migration_metadata,
    waygate_migration_metadata,
)
from .models import (
    Base,
    CompiledDocumentRecord,
    Document,
    DocumentJobLink,
    DocumentType,
    DocumentVectorRef,
    PublishedPageRecord,
    RawDocumentRecord,
    WorkflowJob,
    WorkflowJobTransition,
)

__all__ = [
    "Base",
    "CompiledDocumentRecord",
    "Document",
    "DocumentJobLink",
    "DocumentType",
    "DocumentVectorRef",
    "MIGRATION_ENTRYPOINT_GROUP",
    "PublishedPageRecord",
    "RawDocumentRecord",
    "WorkflowJob",
    "WorkflowJobTransition",
    "discover_migration_metadata",
    "waygate_migration_metadata",
]
