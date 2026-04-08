from importlib import import_module

import anyio
from starlette.responses import PlainTextResponse
from starlette.testclient import TestClient

from waygate_core.settings import RuntimeSettings
from waygate_core.schemas import Visibility

from mcp_server.auth import StaticBearerAuthConfig, StaticBearerAuthMiddleware
from mcp_server.server import create_http_app
from mcp_server.service import BriefingService


class FakeRepository:
    def build_briefing(self, request, scope=None):
        return {"request": request.model_dump(), "scope": scope.model_dump()}

    def retrieve(self, request, scope=None):
        return []


def test_static_bearer_auth_blocks_missing_token() -> None:
    app = StaticBearerAuthMiddleware(
        PlainTextResponse("ok"),
        StaticBearerAuthConfig(enabled=True, token="secret-token"),
    )
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 401
    assert response.json() == {"error": "Unauthorized"}


def test_static_bearer_auth_allows_matching_token() -> None:
    app = StaticBearerAuthMiddleware(
        PlainTextResponse("ok"),
        StaticBearerAuthConfig(enabled=True, token="secret-token"),
    )
    client = TestClient(app)

    response = client.get("/", headers={"Authorization": "Bearer secret-token"})

    assert response.status_code == 200
    assert response.text == "ok"


def test_static_bearer_auth_accepts_case_insensitive_scheme() -> None:
    app = StaticBearerAuthMiddleware(
        PlainTextResponse("ok"),
        StaticBearerAuthConfig(enabled=True, token="secret-token"),
    )
    client = TestClient(app)

    response = client.get("/", headers={"Authorization": "bearer   secret-token"})

    assert response.status_code == 200
    assert response.text == "ok"


def test_create_http_app_reports_auth_state() -> None:
    settings = RuntimeSettings(
        mcp_server_path="/briefing",
        mcp_auth_enabled=False,
    )
    app = create_http_app(BriefingService(FakeRepository()), settings)
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "auth_enabled": False,
        "path": "/briefing",
    }
    assert response.headers["x-trace-id"]


def test_create_http_app_configures_tracing_on_startup(monkeypatch) -> None:
    configured = []
    server_module = import_module("mcp_server.server")
    monkeypatch.setattr(server_module, "configure_tracing", configured.append)

    class _FakeSessionManager:
        def __init__(self) -> None:
            self.entered = 0

        async def __aenter__(self):
            self.entered += 1
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class _FakeRunContext:
        def __init__(self, session_manager: _FakeSessionManager) -> None:
            self.session_manager = session_manager

        async def __aenter__(self):
            await self.session_manager.__aenter__()
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return await self.session_manager.__aexit__(exc_type, exc, tb)

    class _FakeFastMCP:
        def __init__(self) -> None:
            self.session_manager = _FakeSessionManager()
            self.session_manager.run = lambda: _FakeRunContext(self.session_manager)

    fake_mcp = _FakeFastMCP()

    async def run_lifespan() -> None:
        async with server_module.run_mcp_lifespan(fake_mcp):
            return None

    anyio.run(run_lifespan)

    assert configured == ["waygate-mcp-server"]
    assert fake_mcp.session_manager.entered == 1


def test_create_http_app_preserves_incoming_trace_header() -> None:
    settings = RuntimeSettings(
        mcp_server_path="/briefing",
        mcp_auth_enabled=False,
    )
    app = create_http_app(BriefingService(FakeRepository()), settings)
    client = TestClient(app)

    response = client.get("/health", headers={"x-trace-id": "trace-header-1"})

    assert response.status_code == 200
    assert response.headers["x-trace-id"] == "trace-header-1"


def test_create_http_app_mounts_mcp_route() -> None:
    settings = RuntimeSettings(
        mcp_server_path="/briefing",
        mcp_auth_enabled=False,
    )
    app = create_http_app(BriefingService(FakeRepository()), settings)

    with TestClient(app) as client:
        response = client.get(
            "/briefing/",
            follow_redirects=False,
            headers={"host": "127.0.0.1:8000"},
        )

    assert response.status_code == 406
    assert "text/event-stream" in response.text


def test_create_http_app_rejects_enabled_auth_without_token() -> None:
    settings = RuntimeSettings(
        mcp_auth_enabled=True,
        mcp_auth_token=None,
    )

    try:
        create_http_app(BriefingService(FakeRepository()), settings)
    except ValueError as error:
        assert str(error) == "MCP_AUTH_TOKEN must be set when MCP_AUTH_ENABLED=true"
    else:
        raise AssertionError("Expected auth configuration failure")


def test_runtime_settings_support_server_scope_defaults() -> None:
    settings = RuntimeSettings(
        mcp_default_role="ops_agent",
        mcp_allowed_visibilities=[Visibility.PUBLIC],
    )

    assert settings.mcp_default_role == "ops_agent"
    assert settings.mcp_allowed_visibilities == [Visibility.PUBLIC]
