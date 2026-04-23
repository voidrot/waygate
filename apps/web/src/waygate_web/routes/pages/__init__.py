"""Page-route package for the unified WayGate web app."""

from fastapi import APIRouter

from .account import router as account_pages_router
from .control_plane import router as control_plane_router
from .operator import router as operator_pages_router

page_router = APIRouter(tags=["pages"])
page_router.include_router(control_plane_router)
page_router.include_router(operator_pages_router)
page_router.include_router(account_pages_router)

__all__ = ["page_router"]
