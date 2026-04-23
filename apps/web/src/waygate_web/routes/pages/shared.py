"""Shared template helpers for server-rendered page routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fasthx.jinja import Jinja
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
