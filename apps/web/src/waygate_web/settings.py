"""Typed runtime settings for the WayGate web application."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class WaygateWebRuntimeSettings(BaseSettings):
    """Stable non-auth configuration surface for the web package."""

    model_config = SettingsConfigDict(
        env_prefix="WAYGATE_WEB__",
        env_nested_delimiter="__",
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8080, ge=1, le=65535)
    title: str = Field(default="WayGate Web")
    description: str = Field(
        default="Unified WayGate web surface for UI, auth, and webhook ingress."
    )
    version: str = Field(default="0.1.0")
