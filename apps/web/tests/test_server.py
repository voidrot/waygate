from pathlib import Path

from fastapi.testclient import TestClient
from jinja2 import Environment, FileSystemLoader

from waygate_web.server import app


def test_root_dashboard_renders() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "WayGate Control Plane" in response.text
    assert "Runtime summary" in response.text


def test_dashboard_includes_htmx_runtime_refresh_contract() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert 'hx-get="/partials/runtime"' in response.text
    assert 'id="runtime-summary"' in response.text


def test_runtime_partial_renders_server_side_fragment() -> None:
    client = TestClient(app)

    response = client.get("/partials/runtime", headers={"HX-Request": "true"})

    assert response.status_code == 200
    assert "Storage plugin" in response.text
    assert "Communication plugin" in response.text
    assert "Webhook plugins" in response.text


def test_auth_routes_are_registered_on_parent_app() -> None:
    auth_paths = {
        path
        for route in app.routes
        if (path := getattr(route, "path", "")).startswith("/auth")
    }

    assert "/auth/login" in auth_paths


def test_team_index_route_is_registered_on_parent_app() -> None:
    ui_paths = {
        path
        for route in app.routes
        if (path := getattr(route, "path", "")).startswith("/ui")
    }

    assert "/ui/teams" in ui_paths


def test_account_shell_teams_link_targets_team_index() -> None:
    template_root = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "waygate_web"
        / "templates"
        / "authtuna"
        / "user"
    )
    env = Environment(loader=FileSystemLoader(str(template_root)))

    rendered = env.get_template("account_shell.html").render(
        page_title="Account",
        active_page="teams",
    )

    assert 'href="/ui/teams"' in rendered


def test_parent_openapi_includes_mounted_webhook_paths() -> None:
    client = TestClient(app)

    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert "/webhooks/generic-webhook" in schema["paths"]
    assert "GenericWebhookPayload" in schema["components"]["schemas"]
