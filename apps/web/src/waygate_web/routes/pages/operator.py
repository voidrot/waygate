"""Authenticated operator-facing page routes for wiki, documents, jobs, and review work."""

from __future__ import annotations

from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse

from .shared import (
    build_user_template_context,
    page_templates,
    require_authenticated_user,
)

router = APIRouter()


@router.get("/documents", response_class=HTMLResponse)
async def documents_index(
    request: Request,
    q: str | None = None,
    document_type: str | None = None,
    visibility: str | None = None,
    sort: str = "updated_desc",
    metadata_key: str | None = None,
    metadata_value: str | None = None,
) -> HTMLResponse:
    """Render the stub document browser page."""

    current_user = await require_authenticated_user(request)
    context = await build_user_template_context(
        current_user,
        active_page="documents",
        page_title="Documents",
        page_intro=(
            "Browse any tracked document type here. Filtering and sorting contracts "
            "are reserved now so the real metadata-backed query layer can slot in later."
        ),
        filters={
            "q": q or "",
            "document_type": document_type or "",
            "visibility": visibility or "",
            "sort": sort,
            "metadata_key": metadata_key or "",
            "metadata_value": metadata_value or "",
        },
        sort_options=[
            ("updated_desc", "Recently updated"),
            ("updated_asc", "Least recently updated"),
            ("title_asc", "Title A-Z"),
            ("title_desc", "Title Z-A"),
        ],
        stub_documents=[
            {
                "id": "doc-published-policy",
                "title": "Published policy overview",
                "artifact_kind": "published_page",
                "visibility": "public",
                "summary": "Reserved row showing how published pages will appear in the browser.",
            },
            {
                "id": "doc-compile-draft",
                "title": "Compile draft awaiting feedback",
                "artifact_kind": "compiled_document",
                "visibility": "draft",
                "summary": "Reserved row for a compiled draft linked to review activity.",
            },
        ],
        visibility_policy=(
            "Visibility drives access. Current default behavior keeps records visible "
            "unless later enforcement narrows them."
        ),
    )
    return page_templates.TemplateResponse(
        request=request,
        name="documents.html",
        context=context,
    )


@router.get("/documents/{document_id}", response_class=HTMLResponse)
async def document_detail(request: Request, document_id: str) -> HTMLResponse:
    """Render the stub document detail page."""

    current_user = await require_authenticated_user(request)
    context = await build_user_template_context(
        current_user,
        active_page="documents",
        page_title="Document Details",
        page_intro=(
            "This stub reserves the canonical fields and subtype panels needed for any "
            "document tracked by WayGate."
        ),
        document_stub={
            "id": document_id,
            "title": "Document stub",
            "artifact_kind": "published_page",
            "visibility": "public",
            "storage_uri": "storage://published/example.md",
            "source_set_key": "source-set-example",
        },
        detail_sections=[
            "Canonical document fields",
            "Raw document provenance",
            "Compiled document lineage",
            "Published page metadata",
            "Document-job links",
        ],
    )
    return page_templates.TemplateResponse(
        request=request,
        name="document_detail.html",
        context=context,
    )


@router.get("/jobs", response_class=HTMLResponse)
async def jobs_index(
    request: Request,
    workflow_type: str | None = None,
    event_type: str | None = None,
    status_filter: str | None = None,
    source_set_key: str | None = None,
    sort: str = "created_desc",
) -> HTMLResponse:
    """Render the stub workflow job browser page."""

    current_user = await require_authenticated_user(request)
    context = await build_user_template_context(
        current_user,
        active_page="jobs",
        page_title="Workflow Jobs",
        page_intro=(
            "Track compile and related workflow jobs here. The first pass exposes the "
            "filter and detail contracts without requiring live job queries yet."
        ),
        filters={
            "workflow_type": workflow_type or "",
            "event_type": event_type or "",
            "status": status_filter or "",
            "source_set_key": source_set_key or "",
            "sort": sort,
        },
        stub_jobs=[
            {
                "id": "job-compile-001",
                "workflow_type": "draft",
                "event_type": "draft.ready",
                "status": "human_review",
                "source_set_key": "source-set-example",
            },
            {
                "id": "job-publish-002",
                "workflow_type": "review",
                "event_type": "review.completed",
                "status": "completed",
                "source_set_key": "source-set-live",
            },
        ],
    )
    return page_templates.TemplateResponse(
        request=request,
        name="jobs.html",
        context=context,
    )


@router.get("/jobs/{job_id}", response_class=HTMLResponse)
async def job_detail(request: Request, job_id: str) -> HTMLResponse:
    """Render the stub workflow job detail page."""

    current_user = await require_authenticated_user(request)
    context = await build_user_template_context(
        current_user,
        active_page="jobs",
        page_title="Job Details",
        page_intro=(
            "This page reserves the job summary, metrics, transition history, and linked "
            "documents that operators will need once the database query layer is wired in."
        ),
        job_stub={
            "id": job_id,
            "workflow_type": "draft",
            "event_type": "draft.ready",
            "status": "human_review",
            "source_set_key": "source-set-example",
            "last_feedback_summary": "Awaiting a human review decision after revision retries.",
        },
        transition_labels=[
            "ready -> compiling",
            "compiling -> review",
            "review -> human_review",
        ],
    )
    return page_templates.TemplateResponse(
        request=request,
        name="job_detail.html",
        context=context,
    )


@router.get("/reviews", response_class=HTMLResponse)
async def reviews_index(request: Request) -> HTMLResponse:
    """Render the stub human-review queue page."""

    current_user = await require_authenticated_user(request)
    context = await build_user_template_context(
        current_user,
        active_page="reviews",
        page_title="Human Review",
        page_intro=(
            "Drafts that exhaust automated review retries will land here for an operator "
            "decision. This stub page reserves the queue and action vocabulary now."
        ),
        review_queue=[
            {
                "source_set_key": "source-set-example",
                "status": "pending_human_review",
                "revision_count": 3,
                "feedback_count": 2,
            }
        ],
    )
    return page_templates.TemplateResponse(
        request=request,
        name="reviews.html",
        context=context,
    )


@router.get("/reviews/{source_set_key}", response_class=HTMLResponse)
async def review_detail(request: Request, source_set_key: str) -> HTMLResponse:
    """Render the stub human-review detail page."""

    current_user = await require_authenticated_user(request)
    context = await build_user_template_context(
        current_user,
        active_page="reviews",
        page_title="Review Details",
        page_intro=(
            "This page reserves the persisted human-review record shape from the compile "
            "workflow and exposes the future decision actions now."
        ),
        review_record={
            "source_set_key": source_set_key,
            "revision_count": 3,
            "resume_options": ["resume_to_synthesis", "resume_to_publish"],
            "review_feedback": [
                "Clarify the final recommendation and cite the strongest supporting source.",
                "The draft still mixes raw evidence with synthesis without enough separation.",
            ],
            "current_draft": (
                "This is a placeholder excerpt for the current compiled draft that would "
                "be reviewed by a human operator before publication or revision."
            ),
        },
    )
    return page_templates.TemplateResponse(
        request=request,
        name="review_detail.html",
        context=context,
    )


@router.post("/reviews/{source_set_key}/decision", response_class=HTMLResponse)
async def review_decision(
    request: Request,
    source_set_key: str,
    action: str = Form(...),
) -> HTMLResponse:
    """Accept the reserved human-review action names and echo the stub result."""

    current_user = await require_authenticated_user(request)
    if action not in {"resume_to_synthesis", "resume_to_publish"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported review action",
        )

    context = await build_user_template_context(
        current_user,
        action=action,
        source_set_key=source_set_key,
        action_label=(
            "Resume to publish"
            if action == "resume_to_publish"
            else "Resume to synthesis"
        ),
        message=(
            "Decision captured as a UI stub. Actual workflow resume wiring will attach "
            "to this action contract in a later pass."
        ),
    )
    return page_templates.TemplateResponse(
        request=request,
        name="partials/review_action_status.html",
        context=context,
    )
