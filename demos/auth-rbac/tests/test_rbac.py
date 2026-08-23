"""End-to-end RBAC flow tests: login personas, matrix, guards."""

from __future__ import annotations

import httpx
import pytest
from starlette.applications import Starlette

import httpx


async def login_as(client: httpx.AsyncClient, persona: str) -> None:
    """Log the client in as one of the seeded personas."""
    response = await client.post("/api/login", json={"persona": persona})
    assert response.status_code == 200, response.text


def second_browser(app: Starlette) -> httpx.AsyncClient:
    """An independent browser (own cookie jar) over the same app."""
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    )



@pytest.fixture
async def app_fixture(app: Starlette) -> Starlette:
    return app


async def test_login_unknown_persona_422(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/login", json={"persona": "root"})
    assert response.status_code == 422


@pytest.mark.parametrize("persona", ["viewer", "editor", "admin"])
async def test_personas_login_and_report_roles(
    client: httpx.AsyncClient, persona: str
) -> None:
    response = await client.post("/api/login", json={"persona": persona})
    assert response.status_code == 200
    assert response.json()["roles"] == [persona]

    me = await client.get("/api/me")
    assert me.status_code == 200
    assert me.json()["roles"] == [persona]


async def test_matrix_cells_match_expected_rbac(
    client: httpx.AsyncClient,
) -> None:
    matrix = (await client.get("/api/matrix")).json()

    assert set(matrix["personas"]) == {"viewer", "editor", "admin"}
    cells = matrix["cells"]

    # viewer: read-only on articles, nothing on admin_console
    assert cells["viewer"]["articles.view"] is True
    assert cells["viewer"]["articles.create"] is False
    assert cells["viewer"]["admin_console.open"] is False

    # editor: full articles access via `articles.*` wildcard + inheritance
    for check in ("articles.view", "articles.create", "articles.update", "articles.delete"):
        assert cells["editor"][check] is True, check
    assert cells["editor"]["admin_console.open"] is False

    # admin bypasses every check via role-name bypass
    for check in matrix["checks"]:
        assert cells["admin"][check] is True, check


async def test_try_endpoint_matches_matrix(
    client: httpx.AsyncClient,
) -> None:
    granted = await client.post(
        "/api/try",
        json={"role": "editor", "action": "create", "resource": "articles"},
    )
    denied = await client.post(
        "/api/try",
        json={"role": "viewer", "action": "delete", "resource": "articles"},
    )

    assert granted.json() == {
        "granted": True,
        "required": "articles.create",
        "verdict": "Ok(True)",
    }
    body = denied.json()
    assert body["granted"] is False
    assert body["required"] == "articles.delete"


async def test_articles_guarded_by_role(
    client: httpx.AsyncClient, app: Starlette
) -> None:

    # viewer cannot create
    await login_as(client, "viewer")
    denied = await client.post(
        "/api/articles", json={"title": "nope", "body": "denied"}
    )
    assert denied.status_code == 403

    # editor can create; second browser sees it in the listing
    editor = second_browser(app)
    await login_as(editor, "editor")
    created = await editor.post(
        "/api/articles", json={"title": "From editor", "body": "hello"}
    )
    assert created.status_code == 201

    listing = await client.get("/api/articles")
    titles = [a["title"] for a in listing.json()["articles"]]
    assert "From editor" in titles


async def test_me_without_session_is_401(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/me")
    assert response.status_code == 401
    assert "authenticated" in response.json()["detail"]


async def test_articles_require_session(client: httpx.AsyncClient) -> None:
    listing = await client.get("/api/articles")
    assert listing.status_code == 401

    created = await client.post(
        "/api/articles", json={"title": "anon", "body": "nope"}
    )
    assert created.status_code == 401


async def test_login_unknown_persona_problem_detail(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post("/api/login", json={"persona": "ghost"})
    assert response.status_code == 422
    body = response.json()
    assert "unknown persona" in body["detail"]


async def test_try_unknown_persona_is_422(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/try",
        json={"role": "ghost", "action": "view", "resource": "articles"},
    )
    assert response.status_code == 422


async def test_viewer_cannot_update_or_delete(
    client: httpx.AsyncClient,
) -> None:
    """Viewer reads articles but every write path stays closed."""
    await login_as(client, "viewer")

    matrix = (await client.get("/api/matrix")).json()["cells"]["viewer"]
    assert matrix["articles.update"] is False
    assert matrix["articles.delete"] is False

    granted = await client.post(
        "/api/try",
        json={"role": "viewer", "action": "update", "resource": "articles"},
    )
    assert granted.json()["granted"] is False
