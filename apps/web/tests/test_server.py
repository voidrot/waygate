from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from jinja2 import Environment, FileSystemLoader

from waygate_web.routes.pages import control_plane, operator
from waygate_web.server import app


class FakeUser:
    def __init__(self, *, admin: bool = False) -> None:
        self.id = "user-1"
        self.username = "operator"
        self.roles = [
            SimpleNamespace(name="User"),
            *([SimpleNamespace(name="Admin")] if admin else []),
        ]

    def has_role(self, role_name: str) -> bool:
        return any(role.name == role_name for role in self.roles)

    def has_permission(self, permission_name: str) -> bool:
        return permission_name == "admin:access:panel" and self.has_role("Admin")


async def _build_stub_context(user, **context):
    return {**context, "user": user, "user_is_admin": user.has_role("Admin")}


def test_root_dashboard_renders_for_anonymous_users() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "WayGate Control Plane" in response.text
    assert "Signed-in operator work moves to the wiki landing page" in response.text
    assert "Runtime summary" not in response.text


def test_root_renders_wiki_for_authenticated_users(monkeypatch) -> None:
    async def fake_optional_user(_request):
        return FakeUser()

    monkeypatch.setattr(
        control_plane, "get_optional_authenticated_user", fake_optional_user
    )
    monkeypatch.setattr(
        control_plane, "build_user_template_context", _build_stub_context
    )

    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "Published wiki views" in response.text
    assert 'href="/documents"' in response.text
    assert 'href="/jobs"' in response.text
    assert 'href="/reviews"' in response.text
    assert 'href="/ui/runtime"' not in response.text


def test_root_shows_admin_runtime_link_for_admin_users(monkeypatch) -> None:
    async def fake_optional_user(_request):
        return FakeUser(admin=True)

    monkeypatch.setattr(
        control_plane, "get_optional_authenticated_user", fake_optional_user
    )
    monkeypatch.setattr(
        control_plane, "build_user_template_context", _build_stub_context
    )

    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert 'href="/ui/runtime"' in response.text


def test_runtime_page_renders_for_admin_users(monkeypatch) -> None:
    async def fake_admin_user(_request):
        return FakeUser(admin=True)

    monkeypatch.setattr(control_plane, "require_admin_user", fake_admin_user)

    client = TestClient(app)

    response = client.get("/ui/runtime")

    assert response.status_code == 200
    assert "Runtime Summary" in response.text
    assert 'hx-get="/partials/runtime"' in response.text


def test_runtime_page_rejects_non_admin_users(monkeypatch) -> None:
    async def fake_non_admin(_request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    monkeypatch.setattr(control_plane, "require_admin_user", fake_non_admin)

    client = TestClient(app)

    response = client.get("/ui/runtime")

    assert response.status_code == 403


def test_runtime_partial_renders_server_side_fragment_for_admins(monkeypatch) -> None:
    async def fake_admin_user(_request):
        return FakeUser(admin=True)

    monkeypatch.setattr(control_plane, "require_admin_user", fake_admin_user)

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
    assert "/ui/runtime" in ui_paths


def test_operator_routes_are_registered_on_parent_app() -> None:
    paths = {getattr(route, "path", "") for route in app.routes}

    assert "/documents" in paths
    assert "/documents/{document_id}" in paths
    assert "/jobs" in paths
    assert "/jobs/{job_id}" in paths
    assert "/reviews" in paths
    assert "/reviews/{source_set_key}" in paths


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


@pytest.mark.parametrize(
    ("path", "expected_text"),
    [
        ("/documents", "Document browser stub"),
        ("/documents/doc-123", "Reserved detail sections"),
        ("/jobs", "Workflow jobs stub"),
        ("/jobs/job-123", "Transition history stub"),
        ("/reviews", "Human review queue"),
        ("/reviews/source-set-123", "Decision contract"),
    ],
)
def test_operator_pages_render_for_authenticated_users(
    monkeypatch,
    path: str,
    expected_text: str,
) -> None:
    async def fake_authenticated_user(_request):
        return FakeUser()

    monkeypatch.setattr(operator, "require_authenticated_user", fake_authenticated_user)
    monkeypatch.setattr(operator, "build_user_template_context", _build_stub_context)

    client = TestClient(app)

    response = client.get(path)

    assert response.status_code == 200
    assert expected_text in response.text


def test_review_decision_accepts_reserved_action_names(monkeypatch) -> None:
    async def fake_authenticated_user(_request):
        return FakeUser()

    monkeypatch.setattr(operator, "require_authenticated_user", fake_authenticated_user)
    monkeypatch.setattr(operator, "build_user_template_context", _build_stub_context)

    client = TestClient(app)

    response = client.post(
        "/reviews/source-set-123/decision",
        data={"action": "resume_to_publish"},
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
    assert "Resume to publish" in response.text
    assert "source-set-123 :: resume_to_publish" in response.text


def test_review_decision_rejects_unknown_actions(monkeypatch) -> None:
    async def fake_authenticated_user(_request):
        return FakeUser()

    monkeypatch.setattr(operator, "require_authenticated_user", fake_authenticated_user)

    client = TestClient(app)

    response = client.post(
        "/reviews/source-set-123/decision", data={"action": "invalid"}
    )

    assert response.status_code == 400


def test_parent_openapi_includes_mounted_webhook_paths() -> None:
    client = TestClient(app)

    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert "/webhooks/generic-webhook" in schema["paths"]
    assert "GenericWebhookPayload" in schema["components"]["schemas"]
