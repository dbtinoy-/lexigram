"""E2E coverage for the per-user direct permission editing page.

Serves the page the legacy RbacController used to mount at
``/admin/users/{id}/permissions`` through the Resource handler path:
``UserPermissionsActionHandler`` + the ``permissions`` route action.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from httpx import ASGITransport, AsyncClient
import pytest
from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from starlette.routing import Route

from lexigram.admin.config import AdminConfig
from lexigram.admin.resources.handler import ResourceHandler
from lexigram.admin.resources.users import UserResource


class _User:
    """Minimal admin user shape used by the fake data source."""

    def __init__(
        self,
        user_id: str,
        name: str = "Alice",
        email: str = "alice@example.com",
        permissions: list[str] | None = None,
    ) -> None:
        self.user_id = user_id
        self.name = name
        self.email = email
        self.permissions = permissions or []
        self.is_admin = True
        self.role = "admin"


class _MemoryDataSource:
    """In-memory data source with one user and an update log."""

    def __init__(self, user: _User) -> None:
        self.user = user
        self.updates: list[tuple[str, dict]] = []

    async def find_one(self, item_id: object) -> _User | None:
        if str(item_id) == str(self.user.user_id):
            return self.user
        return None

    async def update(self, item_id: object, data: dict) -> _User:
        self.updates.append((str(item_id), data))
        for key, value in data.items():
            setattr(self.user, key, value)
        return self.user


class _FakeInventory:
    """Grouped permission inventory stub (like PermissionInventoryService)."""

    def __init__(self, options: dict[str, list[str]] | None = None) -> None:
        self._options = options or {
            "roles": ["roles.list", "roles.view"],
            "users": ["users.update", "users.view"],
        }

    def options(self) -> dict[str, list[str]]:
        return self._options


def _permissions_resource(user: _User) -> UserResource:
    resource = UserResource()
    resource._data_source = _MemoryDataSource(user)
    resource.permission_inventory = _FakeInventory()
    return resource


def _current_store() -> _MemoryDataSource:
    """Return the data source of the most recently built app."""
    return _LAST_APP["users"]._data_source


_LAST_APP: dict[str, UserResource] = {}


def _app(user: _User | None = None) -> Starlette:
    resource = _permissions_resource(user or _User("u1"))
    _LAST_APP.clear()
    _LAST_APP["users"] = resource
    resources = {"users": resource}

    authenticated_user = user or _User("u1")

    def handler(action: str):
        resource_handler = ResourceHandler(
            AdminConfig(), "users", action, resources=resources
        )

        class AuthenticatedResourceApp:
            async def __call__(self, scope, receive, send):
                # This standalone ASGI fixture must model the authenticated
                # request state that production middleware supplies.
                scope.setdefault("state", {})["user"] = authenticated_user
                return await resource_handler(scope, receive, send)

        return AuthenticatedResourceApp()

    routes = [
        Route(
            "/admin/users/{id}/permissions",
            handler("permissions"),
            methods=["GET", "POST"],
        ),
    ]
    app = Starlette(routes=routes)
    app.state.nav_builder = None
    app.add_middleware(SessionMiddleware, secret_key="test-secret-key-for-tests")
    return app


@asynccontextmanager
async def _client(user: _User | None = None):
    """Yield an AsyncClient bound to a freshly built app."""
    app = _app(user=user)
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://testserver", follow_redirects=False
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_permissions_form_renders_grouped_checkboxes() -> None:
    async with _client() as client:
        r = await client.get("/admin/users/u1/permissions")
        assert r.status_code == 200
        assert 'name="permissions"' in r.text
        assert "roles.list" in r.text
        assert "users.update" in r.text
        assert 'name="csrf_token"' in r.text


@pytest.mark.asyncio
async def test_permissions_form_pre_checks_selected() -> None:
    async with _client(user=_User("u1", permissions=["roles.list", "*"])) as client:
        r = await client.get("/admin/users/u1/permissions")
        assert r.status_code == 200
        assert 'value="roles.list"' in r.text
        assert 'value="*"' in r.text
        assert 'name="csrf_token"' in r.text


@pytest.mark.asyncio
async def test_permissions_submit_updates_user() -> None:
    async with _client() as client:
        r = await client.post(
            "/admin/users/u1/permissions",
            data={"permissions": "roles.view", "csrf_token": "x"},
        )
        assert r.status_code == 302
        assert "notice=" in r.headers["location"]
        store = _current_store()
        assert store.user.permissions == ["roles.view"]


@pytest.mark.asyncio
async def test_permissions_submit_sorts_and_deduplicates() -> None:
    async with _client() as client:
        await client.post(
            "/admin/users/u1/permissions",
            data={"permissions": ["users.view", "roles.list", "users.view"]},
        )
        store = _current_store()
        assert store.user.permissions == ["roles.list", "users.view"]


@pytest.mark.asyncio
async def test_permissions_unknown_user_404() -> None:
    async with _client() as client:
        r = await client.get("/admin/users/nobody/permissions")
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_permissions_submit_unknown_user_redirects_with_error() -> None:
    async with _client() as client:
        r = await client.post(
            "/admin/users/nobody/permissions",
            data={"permissions": "roles.view", "csrf_token": "x"},
        )
        assert r.status_code == 302
        assert "error=" in r.headers["location"]


def test_permissions_action_url() -> None:
    from types import SimpleNamespace

    from lexigram.admin.actions import PermissionsAction
    from lexigram.admin.actions.types import ActionContext

    action = PermissionsAction()
    ctx = ActionContext(resource_name="users", resource_prefix="/admin/users")
    assert (
        action._get_url(
            SimpleNamespace(id="u1"),
            ctx,
        )
        == "/admin/users/u1/permissions"
    )
