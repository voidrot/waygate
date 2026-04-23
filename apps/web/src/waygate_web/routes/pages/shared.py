"""Shared template helpers for server-rendered page routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fasthx.jinja import Jinja
from fastapi import HTTPException, Request, status
from fastapi.templating import Jinja2Templates

_template_root = Path(__file__).resolve().parents[2] / "templates"

page_templates = Jinja2Templates(directory=str(_template_root))
auth_user_templates = Jinja2Templates(
    directory=str(_template_root / "authtuna" / "user")
)
page_jinja = Jinja(page_templates)


def unwrap_template_entity(entity: Any) -> Any:
    """Return ORM entities from SQLAlchemy row wrappers when needed."""

    mapping = getattr(entity, "_mapping", None)
    if mapping:
        return next(iter(mapping.values()))
    if isinstance(entity, tuple):
        return entity[0]
    return entity


async def get_optional_authenticated_user(request: Request) -> Any | None:
    """Resolve the current authenticated user when a session exists."""

    current_user = getattr(request.state, "user_object", None)
    if current_user is not None:
        return current_user

    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        return None

    from authtuna.integrations.fastapi_integration import auth_service

    return await auth_service.users.get_by_id(user_id, with_relations=True)


async def require_authenticated_user(request: Request) -> Any:
    """Return the current authenticated user or raise 401."""

    current_user = await get_optional_authenticated_user(request)
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return current_user


async def is_admin_user(user: Any | None) -> bool:
    """Return whether the user has global admin access."""

    if user is None:
        return False

    has_role = getattr(user, "has_role", None)
    if callable(has_role) and (has_role("Admin") or has_role("SuperAdmin")):
        return True

    has_permission = getattr(user, "has_permission", None)
    if callable(has_permission) and has_permission("admin:access:panel"):
        return True

    user_id = getattr(user, "id", None)
    if user_id is None:
        return False

    try:
        from authtuna.integrations.fastapi_integration import auth_service

        return await auth_service.roles.has_permission(
            str(user_id),
            "admin:access:panel",
        )
    except Exception:
        return False


async def require_admin_user(request: Request) -> Any:
    """Return the current authenticated admin user or raise 403."""

    current_user = await require_authenticated_user(request)
    if not await is_admin_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def build_user_template_context(
    user: Any | None, **context: Any
) -> dict[str, Any]:
    """Attach shared user-derived template context for page rendering."""

    template_context = dict(context)
    if user is not None:
        template_context.setdefault("user", user)
    template_context.setdefault("user_is_admin", await is_admin_user(user))
    return template_context
