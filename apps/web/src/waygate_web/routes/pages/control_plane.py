"""Public control-plane pages and HTMX fragments."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from waygate_core import get_app_context

from .shared import page_jinja

router = APIRouter()


@router.get("/")
@page_jinja.page("dashboard.html")
async def dashboard() -> dict[str, Any]:
    """Render the main operator dashboard shell."""

    app_context = get_app_context()
    plugin_counts = {
        "webhooks": len(app_context.plugins.webhooks),
        "communication": len(app_context.plugins.communication),
        "storage": len(app_context.plugins.storage),
        "llm": len(app_context.plugins.llm),
    }
    return {
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
    }


@router.get("/partials/runtime")
@page_jinja.hx("partials/runtime_summary.html")
async def runtime_summary() -> dict[str, Any]:
    """Render a small HTMX fragment summarizing the current runtime."""

    app_context = get_app_context()
    return {
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
    }
