"""Canonical SQLAlchemy declarative models for WayGate database tables."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID as PyUUID, uuid7

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from waygate_core.schema.visibility import Visibility


def _uuid7_uuid() -> PyUUID:
    """Return a UUIDv7 object for first-party ORM primary keys."""

    return uuid7()


def _utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp for ORM defaults."""

    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Base declarative model for first-party WayGate ORM tables."""


class DocumentType(Base):
    """Semantic document taxonomy used across raw, compiled, and published artifacts."""

    __tablename__ = "document_types"

    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=_uuid7_uuid,
        server_default=text("uuidv7()"),
    )
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text())
    metadata_schema: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    metadata_defaults: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        onupdate=func.now(),
        server_default=func.now(),
    )


class WorkflowJob(Base):
    """Workflow execution row used for generic job status and metrics tracking."""

    __tablename__ = "workflow_jobs"

    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=_uuid7_uuid,
        server_default=text("uuidv7()"),
    )
    request_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    workflow_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_source: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="pending")
    source_set_key: Mapped[str | None] = mapped_column(String(255))
    revision_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    reject_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    last_feedback_summary: Mapped[str | None] = mapped_column(Text())
    job_details: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    metrics: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        onupdate=func.now(),
        server_default=func.now(),
    )


class Document(Base):
    """Shared registry row for every tracked raw, compiled, and published artifact."""

    __tablename__ = "documents"

    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=_uuid7_uuid,
        server_default=text("uuidv7()"),
    )
    artifact_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    document_type_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_types.id", ondelete="RESTRICT"),
        nullable=False,
    )
    storage_uri: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    visibility: Mapped[Visibility] = mapped_column(
        SQLEnum(
            Visibility,
            native_enum=False,
            values_callable=lambda values: [value.value for value in values],
            name="document_visibility",
        ),
        nullable=False,
        default=Visibility.PUBLIC,
        server_default=Visibility.PUBLIC.value,
    )
    title: Mapped[str | None] = mapped_column(String(255))
    summary: Mapped[str | None] = mapped_column(Text())
    current_content_hash: Mapped[str | None] = mapped_column(String(255), index=True)
    source_hash: Mapped[str | None] = mapped_column(String(255), index=True)
    source_uri: Mapped[str | None] = mapped_column(String(1024), index=True)
    source_set_key: Mapped[str | None] = mapped_column(String(255), index=True)
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    topics: Mapped[list[str]] = mapped_column(
        ARRAY(Text()), nullable=False, default=list
    )
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text()), nullable=False, default=list)
    people: Mapped[list[str]] = mapped_column(
        ARRAY(Text()), nullable=False, default=list
    )
    organizations: Mapped[list[str]] = mapped_column(
        ARRAY(Text()),
        nullable=False,
        default=list,
    )
    projects: Mapped[list[str]] = mapped_column(
        ARRAY(Text()),
        nullable=False,
        default=list,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        onupdate=func.now(),
        server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_documents_metadata_gin", "metadata", postgresql_using="gin"),
        Index("ix_documents_topics_gin", "topics", postgresql_using="gin"),
        Index("ix_documents_tags_gin", "tags", postgresql_using="gin"),
        Index("ix_documents_people_gin", "people", postgresql_using="gin"),
        Index(
            "ix_documents_organizations_gin",
            "organizations",
            postgresql_using="gin",
        ),
        Index("ix_documents_projects_gin", "projects", postgresql_using="gin"),
    )


class RawDocumentRecord(Base):
    """Raw-ingest specific provenance and source fields for tracked documents."""

    __tablename__ = "raw_documents"

    document_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        primary_key=True,
    )
    source_type: Mapped[str] = mapped_column(String(255), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(255))
    content_type: Mapped[str | None] = mapped_column(String(255))
    source_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    raw_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CompiledDocumentRecord(Base):
    """Compile-specific durable fields for compiled document artifacts."""

    __tablename__ = "compiled_documents"

    document_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        primary_key=True,
    )
    compiled_document_id: Mapped[str] = mapped_column(String(255), nullable=False)
    compiled_document_hash: Mapped[str | None] = mapped_column(String(255), index=True)
    compiled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_document_uris: Mapped[list[str]] = mapped_column(
        ARRAY(Text()),
        nullable=False,
        default=list,
    )
    source_content_hashes: Mapped[list[str]] = mapped_column(
        ARRAY(Text()),
        nullable=False,
        default=list,
    )
    source_hashes: Mapped[list[str]] = mapped_column(
        ARRAY(Text()),
        nullable=False,
        default=list,
    )
    source_uris: Mapped[list[str]] = mapped_column(
        ARRAY(Text()),
        nullable=False,
        default=list,
    )
    review_feedback: Mapped[list[str]] = mapped_column(
        ARRAY(Text()),
        nullable=False,
        default=list,
    )
    compile_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )


class PublishedPageRecord(Base):
    """Published page lineage and metadata built from compiled artifacts."""

    __tablename__ = "published_pages"

    document_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        primary_key=True,
    )
    published_page_id: Mapped[str] = mapped_column(String(255), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    compiled_document_ids: Mapped[list[str]] = mapped_column(
        ARRAY(Text()),
        nullable=False,
        default=list,
    )
    compiled_document_uris: Mapped[list[str]] = mapped_column(
        ARRAY(Text()),
        nullable=False,
        default=list,
    )
    source_set_keys: Mapped[list[str]] = mapped_column(
        ARRAY(Text()),
        nullable=False,
        default=list,
    )
    page_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )


class WorkflowJobTransition(Base):
    """Append-only job status transition history for workflow observability."""

    __tablename__ = "workflow_job_transitions"

    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=_uuid7_uuid,
        server_default=text("uuidv7()"),
    )
    job_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_status: Mapped[str | None] = mapped_column(String(64))
    to_status: Mapped[str] = mapped_column(String(64), nullable=False)
    transition_reason: Mapped[str | None] = mapped_column(Text())
    metrics: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    context: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    transitioned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        server_default=func.now(),
    )


class DocumentJobLink(Base):
    """Document/job history rows that retain every edit relationship."""

    __tablename__ = "document_job_links"

    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=_uuid7_uuid,
        server_default=text("uuidv7()"),
    )
    document_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    edit_type: Mapped[str] = mapped_column(String(64), nullable=False)
    edit_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    first_edit_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        server_default=func.now(),
    )
    last_edit_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        server_default=func.now(),
    )
    context: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "job_id",
            "edit_type",
            name="uq_document_job_links_document_job_edit_type",
        ),
    )


class DocumentVectorRef(Base):
    """Generic downstream vector/index references derived from stored documents."""

    __tablename__ = "document_vector_refs"

    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=_uuid7_uuid,
        server_default=text("uuidv7()"),
    )
    document_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    backend_name: Mapped[str] = mapped_column(String(128), nullable=False)
    collection_name: Mapped[str | None] = mapped_column(String(255))
    namespace: Mapped[str | None] = mapped_column(String(255))
    external_document_id: Mapped[str | None] = mapped_column(String(255))
    chunk_id: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="pending")
    metadata_payload: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
        onupdate=func.now(),
        server_default=func.now(),
    )


__all__ = [
    "Base",
    "CompiledDocumentRecord",
    "Document",
    "DocumentJobLink",
    "DocumentType",
    "DocumentVectorRef",
    "PublishedPageRecord",
    "RawDocumentRecord",
    "WorkflowJob",
    "WorkflowJobTransition",
]
