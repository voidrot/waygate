"""Authenticated account-facing page routes rendered by the web app."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse

from .shared import auth_user_templates, unwrap_template_entity

router = APIRouter()


async def _get_authenticated_user(request: Request) -> Any:
    """Resolve the current authenticated AuthTuna user from request state."""

    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    current_user = getattr(request.state, "user_object", None)
    if current_user is not None:
        return current_user

    from authtuna.integrations.fastapi_integration import auth_service

    current_user = await auth_service.users.get_by_id(user_id, with_relations=True)
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found for this session",
        )
    return current_user


@router.get("/ui/teams", response_class=HTMLResponse)
async def teams_dashboard(request: Request) -> HTMLResponse:
    """Render the user's team memberships grouped by organization."""

    from authtuna.integrations.fastapi_integration import auth_service

    current_user = await _get_authenticated_user(request)
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

    return auth_user_templates.TemplateResponse(
        request=request,
        name="teams.html",
        context={
            "user": current_user,
            "team_groups": team_groups,
        },
    )
