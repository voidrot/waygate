from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from receiver.core.registry import registry
from receiver.services.settings import (
    SettingsAdminService,
    build_settings_namespace_registry,
)
from waygate_core.settings import get_runtime_settings
from waygate_core.settings_store import PostgresSettingsStore

router = APIRouter(prefix="/admin/settings", tags=["settings"])


class SettingsUpdateRequest(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)


def get_settings_service() -> SettingsAdminService:
    runtime_settings = get_runtime_settings()
    if not registry.get_all():
        registry.discover_and_register()

    store = None
    if runtime_settings.postgres_dsn:
        store = PostgresSettingsStore(runtime_settings.postgres_dsn)

    return SettingsAdminService(
        namespace_registry=build_settings_namespace_registry(registry.get_all()),
        runtime_settings_backend=runtime_settings.runtime_settings_backend,
        store=store,
    )


@router.get("")
def list_settings_namespaces(
    service: SettingsAdminService = Depends(get_settings_service),
):
    return {"namespaces": service.list_namespaces()}


@router.get("/{namespace}")
def get_settings_namespace(
    namespace: str,
    service: SettingsAdminService = Depends(get_settings_service),
):
    try:
        return service.get_namespace(namespace)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{namespace}")
def update_settings_namespace(
    namespace: str,
    request: SettingsUpdateRequest,
    service: SettingsAdminService = Depends(get_settings_service),
):
    try:
        return service.update_namespace(namespace, request.values)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
