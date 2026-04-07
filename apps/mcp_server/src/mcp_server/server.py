from __future__ import annotations

import contextlib

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from mcp.server.fastmcp import FastMCP

from waygate_agent_sdk import BriefingResult
from waygate_agent_sdk.models import RetrievedLiveDocument
from waygate_core.settings import RuntimeSettings

from mcp_server.auth import StaticBearerAuthConfig, StaticBearerAuthMiddleware
from mcp_server.config import briefing_service, settings
from mcp_server.service import BriefingService, GenerateBriefingRequest


def create_mcp_server(service: BriefingService) -> FastMCP:
    mcp = FastMCP(
        "WayGate Briefing Server",
        instructions=(
            "Retrieve and compile token-budgeted briefings from the live WayGate wiki."
        ),
        json_response=True,
        stateless_http=True,
        streamable_http_path="/",
    )

    @mcp.tool()
    def generate_briefing(request: GenerateBriefingRequest) -> BriefingResult:
        """Generate a filtered briefing from the compiled live wiki."""
        return service.generate_briefing(request)

    @mcp.tool()
    def preview_retrieval(
        request: GenerateBriefingRequest,
    ) -> list[RetrievedLiveDocument]:
        """Preview ranked retrieval results without assembling a briefing."""
        return service.preview_retrieval(request)

    return mcp


def create_http_app(
    service: BriefingService,
    runtime_settings: RuntimeSettings,
) -> Starlette:
    mcp_server = create_mcp_server(service)
    mcp_app = mcp_server.streamable_http_app()
    auth_config = StaticBearerAuthConfig.from_settings(runtime_settings)
    if auth_config.enabled:
        mcp_app = StaticBearerAuthMiddleware(mcp_app, auth_config)

    async def healthcheck(_) -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "auth_enabled": auth_config.enabled,
                "path": runtime_settings.mcp_server_path,
            }
        )

    @contextlib.asynccontextmanager
    async def lifespan(_: Starlette):
        async with mcp_server.session_manager.run():
            yield

    return Starlette(
        lifespan=lifespan,
        routes=[
            Route("/health", healthcheck),
            Mount(runtime_settings.mcp_server_path, app=mcp_app),
        ],
    )


mcp = create_mcp_server(briefing_service)
app = create_http_app(briefing_service, settings)
