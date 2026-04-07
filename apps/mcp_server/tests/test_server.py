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
