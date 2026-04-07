from __future__ import annotations

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from waygate_core.settings import RuntimeSettings


class StaticBearerAuthConfig:
    def __init__(self, enabled: bool = False, token: str | None = None):
        self.enabled = enabled
        self.token = token

    @classmethod
    def from_settings(cls, settings: RuntimeSettings) -> "StaticBearerAuthConfig":
        if settings.mcp_auth_enabled and not settings.mcp_auth_token:
            raise ValueError("MCP_AUTH_TOKEN must be set when MCP_AUTH_ENABLED=true")
        return cls(
            enabled=settings.mcp_auth_enabled,
            token=settings.mcp_auth_token,
        )


class StaticBearerAuthMiddleware:
    def __init__(self, app: ASGIApp, config: StaticBearerAuthConfig):
        self.app = app
        self.config = config

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not self.config.enabled:
            await self.app(scope, receive, send)
            return

        if scope["method"] == "OPTIONS":
            await self.app(scope, receive, send)
            return

        authorization = Headers(scope=scope).get("authorization")
        expected = f"Bearer {self.config.token}"
        if authorization == expected:
            await self.app(scope, receive, send)
            return

        response = JSONResponse(
            {"error": "Unauthorized"},
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
        )
        await response(scope, receive, send)
