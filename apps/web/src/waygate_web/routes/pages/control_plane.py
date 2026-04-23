"""Public control-plane pages and HTMX fragments."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from waygate_core import get_app_context

from .shared import (
    build_user_template_context,
    get_optional_authenticated_user,
    page_templates,
    require_admin_user,
)

router = APIRouter()


@router.get("/")
async def dashboard(request: Request) -> HTMLResponse:
    """Render the public splash or authenticated wiki landing page."""

    app_context = get_app_context()
    plugin_counts = {
        "webhooks": len(app_context.plugins.webhooks),
        "communication": len(app_context.plugins.communication),
        "storage": len(app_context.plugins.storage),
        "llm": len(app_context.plugins.llm),
    }
    current_user = await get_optional_authenticated_user(request)
    if current_user is None:
        return page_templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={
                "page_title": "WayGate Control Plane",
                "mounts": [
                    {
                        "label": "Webhook ingress",
                        "href": "/docs#tag/webhooks",
                        "description": "Mounted FastAPI sub-app with merged OpenAPI docs.",
                    },
                    {
                        "label": "Auth flows",
                        "href": "/auth/login",
                        "description": "AuthTuna-provided sign-in and token surfaces.",
                    },
                ],
                "plugin_counts": plugin_counts,
            },
        )

    context = await build_user_template_context(
        current_user,
        active_page="wiki",
        page_title="Wiki",
        page_intro=(
            "Published content becomes the signed-in landing surface. "
            "This first pass reserves the document lenses and navigation "
            "contracts without requiring live database queries yet."
        ),
        published_sections=[
            {
                "title": "Published pages",
                "description": (
                    "This area will list published pages from the database with "
                    "titles, summaries, timestamps, and source lineage."
                ),
            },
            {
                "title": "Metadata lenses",
                "description": (
                    "Topic, tag, person, organization, and project views will be "
                    "derived from published document metadata."
                ),
            },
            {
                "title": "Recent changes",
                "description": (
                    "Recent publish and compile activity will surface here once the "
                    "document and job indexes are wired into the web app."
                ),
            },
        ],
        visibility_policy=(
            "Visibility governs access. The current default behavior keeps content "
            "open unless later restrictions narrow it."
        ),
        plugin_counts=plugin_counts,
    )
    return page_templates.TemplateResponse(
        request=request,
        name="wiki.html",
        context=context,
    )


@router.get("/ui/runtime", response_class=HTMLResponse)
async def runtime_page(request: Request) -> HTMLResponse:
    """Render the admin-only runtime summary page."""

    current_user = await require_admin_user(request)
    return page_templates.TemplateResponse(
        request=request,
        name="runtime.html",
        context={
            "user": current_user,
            "user_is_admin": True,
            "active_page": "runtime",
            "page_title": "Runtime Summary",
            "page_intro": (
                "Operational runtime details remain available, but now live on a "
                "dedicated admin-only page instead of the signed-in landing screen."
            ),
        },
    )


@router.get("/partials/runtime")
async def runtime_summary(request: Request) -> HTMLResponse:
    """Render the admin-only HTMX runtime summary fragment."""

    await require_admin_user(request)

    app_context = get_app_context()
    return page_templates.TemplateResponse(
        request=request,
        name="partials/runtime_summary.html",
        context={
            "runtime_rows": [
                ("Storage plugin", app_context.config.core.storage_plugin_name),
                (
                    "Communication plugin",
                    app_context.config.core.communication_plugin_name,
                ),
                (
                    "Webhook plugins",
                    ", ".join(sorted(app_context.plugins.webhooks.keys())) or "none",
                ),
            ]
        },
    )
