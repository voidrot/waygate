from __future__ import annotations

from sqlalchemy.dialects import postgresql

from waygate_core.database.models import Base


def test_core_database_models_register_expected_tables() -> None:
    expected_tables = {
        "document_types",
        "documents",
        "raw_documents",
        "compiled_documents",
        "published_pages",
        "workflow_jobs",
        "workflow_job_transitions",
        "document_job_links",
        "document_vector_refs",
    }

    assert expected_tables.issubset(Base.metadata.tables)


def test_documents_table_includes_searchable_metadata_and_audit_columns() -> None:
    documents = Base.metadata.tables["documents"]

    assert isinstance(documents.c.id.type, postgresql.UUID)
    assert "artifact_kind" in documents.c
    assert "document_type_id" in documents.c
    assert "storage_uri" in documents.c
    assert "current_content_hash" in documents.c
    assert "source_hash" in documents.c
    assert "source_uri" in documents.c
    assert "source_set_key" in documents.c
    assert "metadata" in documents.c
    assert "topics" in documents.c
    assert "tags" in documents.c
    assert "people" in documents.c
    assert "organizations" in documents.c
    assert "projects" in documents.c
    assert "created_at" in documents.c
    assert "updated_at" in documents.c


def test_workflow_jobs_and_transitions_include_generic_job_tracking_fields() -> None:
    jobs = Base.metadata.tables["workflow_jobs"]
    transitions = Base.metadata.tables["workflow_job_transitions"]

    assert isinstance(jobs.c.id.type, postgresql.UUID)
    assert "request_key" in jobs.c
    assert "workflow_type" in jobs.c
    assert "event_type" in jobs.c
    assert "status" in jobs.c
    assert "reject_count" in jobs.c
    assert "revision_count" in jobs.c
    assert "metrics" in jobs.c
    assert "created_at" in jobs.c
    assert "updated_at" in jobs.c

    assert isinstance(transitions.c.id.type, postgresql.UUID)
    assert isinstance(transitions.c.job_id.type, postgresql.UUID)
    assert "job_id" in transitions.c
    assert "from_status" in transitions.c
    assert "to_status" in transitions.c
    assert "transition_reason" in transitions.c
    assert "transitioned_at" in transitions.c
    assert "metrics" in transitions.c


def test_document_job_links_capture_all_job_edits_for_a_document() -> None:
    links = Base.metadata.tables["document_job_links"]

    assert isinstance(links.c.id.type, postgresql.UUID)
    assert isinstance(links.c.document_id.type, postgresql.UUID)
    assert isinstance(links.c.job_id.type, postgresql.UUID)
    assert "document_id" in links.c
    assert "job_id" in links.c
    assert "edit_type" in links.c
    assert "edit_count" in links.c
    assert "first_edit_at" in links.c
    assert "last_edit_at" in links.c

    unique_constraints = {
        tuple(sorted(column.name for column in constraint.columns))
        for constraint in links.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }

    assert ("document_id", "edit_type", "job_id") in unique_constraints


def test_artifact_specific_tables_reference_documents() -> None:
    for table_name in ("raw_documents", "compiled_documents", "published_pages"):
        table = Base.metadata.tables[table_name]
        assert isinstance(table.c.document_id.type, postgresql.UUID)
        assert "document_id" in table.c


def test_document_vector_refs_store_backend_specific_reference_payload() -> None:
    vector_refs = Base.metadata.tables["document_vector_refs"]

    assert isinstance(vector_refs.c.id.type, postgresql.UUID)
    assert isinstance(vector_refs.c.document_id.type, postgresql.UUID)
    assert "document_id" in vector_refs.c
    assert "backend_name" in vector_refs.c
    assert "collection_name" in vector_refs.c
    assert "external_document_id" in vector_refs.c
    assert "chunk_id" in vector_refs.c
    assert "status" in vector_refs.c
    assert "metadata" in vector_refs.c


def test_uuid_primary_keys_use_uuidv7_server_defaults() -> None:
    for table_name in (
        "document_types",
        "workflow_jobs",
        "documents",
        "workflow_job_transitions",
        "document_job_links",
        "document_vector_refs",
    ):
        table = Base.metadata.tables[table_name]
        assert str(table.c.id.server_default.arg) == "uuidv7()"
