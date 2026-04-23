"""Authenticated account-facing page routes rendered by the web app."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from .shared import (
    auth_user_templates,
    build_user_template_context,
    require_authenticated_user,
    unwrap_template_entity,
)

router = APIRouter()


@router.get("/ui/teams", response_class=HTMLResponse)
async def teams_dashboard(request: Request) -> HTMLResponse:
    """Render the user's team memberships grouped by organization."""

    from authtuna.integrations.fastapi_integration import auth_service

    current_user = await require_authenticated_user(request)
    user_teams_by_org = await auth_service.orgs.get_user_teams(str(current_user.id))

    team_groups = []
    for org, team_rows in user_teams_by_org.items():
        teams = [unwrap_template_entity(team_row) for team_row in team_rows]
        if not teams:
            continue
        team_groups.append(
            {
                "org": unwrap_template_entity(org),
                "teams": teams,
            }
        )

    context = await build_user_template_context(
        current_user,
        team_groups=team_groups,
    )
    return auth_user_templates.TemplateResponse(
        request=request,
        name="teams.html",
        context=context,
    )
