"""E2E HTTP tests for the RBAC editing pages (roles + user roles)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from httpx import ASGITransport, AsyncClient
import pytest
from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from lexigram.admin.controllers.rbac import RbacController
from lexigram.admin.rbac.types import AdminRole
from lexigram.result import Err, Ok


def _make_role_service() -> MagicMock:
    svc = MagicMock()
    svc.list_roles = AsyncMock(
        return_value=[
            AdminRole("admin", "Admins", ["roles.view", "roles.update"], [], True)
        ]
    )
    svc.create_role = AsyncMock(return_value=Ok(AdminRole("editor", "Editors")))
    svc.update_role = AsyncMock(return_value=Ok(AdminRole("editor", "Editors v2")))
    svc.delete_role = AsyncMock(return_value=Ok(None))
    return svc


def _make_user_store() -> MagicMock:
    store = MagicMock()
    user = MagicMock()
    user.user_id = "u1"
    user.name = "Admin"
    user.email = "admin@example.com"
    user.roles = ["admin"]
    store.list_users = AsyncMock(return_value=[user])
    store.update_user = AsyncMock(return_value=user)
    return store


def _make_csrf_service(*, valid: bool = True) -> MagicMock:
    svc = MagicMock()
    svc.generate_token = MagicMock(return_value="csrf-test-token")
    svc.validate_token = MagicMock(return_value=valid)
    return svc


class _DummyRenderer:
    def render_page(self, content, request=None, title=None, breadcrumbs=None):
        return PlainTextResponse(str(content))


def create_app(*, csrf_valid: bool = True, delete_error: bool = False) -> Starlette:
    role_service = _make_role_service()
    user_store = _make_user_store()
    if delete_error:
        from lexigram.admin.rbac.errors import SystemRoleError

        role_service.delete_role = AsyncMock(return_value=Err(SystemRoleError("no")))
    controller = RbacController(
        csrf_service=_make_csrf_service(valid=csrf_valid),
        renderer=_DummyRenderer(),
        role_service=role_service,
        user_store=user_store,
    )

    async def roles_list(request):
        return await controller.roles_list(request)

    async def role_new_form(request):
        return await controller.role_new_form(request)

    async def role_new_submit(request):
        return await controller.role_new_submit(request)

    async def role_edit_form(request):
        return await controller.role_edit_form(request)

    async def role_edit_submit(request):
        return await controller.role_edit_submit(request)

    async def role_delete_submit(request):
        return await controller.role_delete_submit(request)

    async def users_list(request):
        return await controller.users_list(request)

    async def user_roles_form(request):
        return await controller.user_roles_form(request)

    async def user_roles_submit(request):
        return await controller.user_roles_submit(request)

    routes = [
        Route("/admin/roles", roles_list, methods=["GET"]),
        Route("/admin/roles/new", role_new_form, methods=["GET"]),
        Route("/admin/roles/new", role_new_submit, methods=["POST"]),
        Route("/admin/roles/{name}/edit", role_edit_form, methods=["GET"]),
        Route("/admin/roles/{name}/edit", role_edit_submit, methods=["POST"]),
        Route("/admin/roles/{name}/delete", role_delete_submit, methods=["POST"]),
        Route("/admin/users", users_list, methods=["GET"]),
        Route("/admin/users/{user_id}/roles", user_roles_form, methods=["GET"]),
        Route("/admin/users/{user_id}/roles", user_roles_submit, methods=["POST"]),
    ]

    app = Starlette(routes=routes)
    app.add_middleware(SessionMiddleware, secret_key="test-secret-key-for-tests")
    app.state.user_store = user_store
    app.state.role_service = role_service
    return app


@pytest.mark.asyncio
async def test_roles_list_renders_roles() -> None:
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app), base_url="http://testserver"
    ) as client:
        r = await client.get("/admin/roles")
        assert r.status_code == 200
        assert "admin" in r.text
        assert "/admin/roles/new" in r.text


@pytest.mark.asyncio
async def test_role_new_form_has_csrf_and_groups() -> None:
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app), base_url="http://testserver"
    ) as client:
        r = await client.get("/admin/roles/new")
        assert r.status_code == 200
        assert "csrf-test-token" in r.text
        assert 'name="permissions"' in r.text
        assert "roles.list" in r.text


@pytest.mark.asyncio
async def test_role_new_submit_redirects_with_notice() -> None:
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        await client.get("/admin/roles/new")  # establishes csrf session
        r = await client.post(
            "/admin/roles/new",
            data={
                "name": "editor",
                "description": "Editors",
                "permissions": "roles.view",
                "csrf_token": "csrf-test-token",
            },
        )
        assert r.status_code == 302
        assert "notice=" in r.headers["location"]


@pytest.mark.asyncio
async def test_role_new_submit_invalid_csrf_redirects_with_error() -> None:
    app = create_app(csrf_valid=False)
    async with AsyncClient(
        transport=ASGITransport(app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        await client.get("/admin/roles/new")
        r = await client.post(
            "/admin/roles/new",
            data={"name": "x", "csrf_token": "csrf-test-token"},
        )
        assert r.status_code == 302
        assert "error=" in r.headers["location"]


@pytest.mark.asyncio
async def test_role_edit_form_pre_checks_permissions() -> None:
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app), base_url="http://testserver"
    ) as client:
        r = await client.get("/admin/roles/admin/edit")
        assert r.status_code == 200
        assert "checked" in r.text


@pytest.mark.asyncio
async def test_role_edit_submit_redirects_with_notice() -> None:
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        await client.get("/admin/roles/admin/edit")
        r = await client.post(
            "/admin/roles/admin/edit",
            data={
                "name": "admin",
                "description": "Admins",
                "csrf_token": "csrf-test-token",
            },
        )
        assert r.status_code == 302
        assert "notice=" in r.headers["location"]


@pytest.mark.asyncio
async def test_role_delete_submit_redirects() -> None:
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        await client.get("/admin/roles")
        r = await client.post(
            "/admin/roles/editor/delete",
            data={"csrf_token": "csrf-test-token"},
        )
        assert r.status_code == 302


@pytest.mark.asyncio
async def test_role_delete_system_role_redirects_with_error() -> None:
    app = create_app(delete_error=True)
    async with AsyncClient(
        transport=ASGITransport(app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        await client.get("/admin/roles")
        r = await client.post(
            "/admin/roles/admin/delete",
            data={"csrf_token": "csrf-test-token"},
        )
        assert r.status_code == 302
        assert "error=" in r.headers["location"]


@pytest.mark.asyncio
async def test_users_list_renders_users_with_roles() -> None:
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app), base_url="http://testserver"
    ) as client:
        r = await client.get("/admin/users")
        assert r.status_code == 200
        assert "admin@example.com" in r.text
        assert "admin" in r.text


@pytest.mark.asyncio
async def test_user_roles_form_renders_role_checkboxes() -> None:
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app), base_url="http://testserver"
    ) as client:
        r = await client.get("/admin/users/u1/roles")
        assert r.status_code == 200
        assert 'name="roles"' in r.text
        assert "admin" in r.text


@pytest.mark.asyncio
async def test_user_roles_submit_updates_user() -> None:
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        await client.get("/admin/users/u1/roles")
        r = await client.post(
            "/admin/users/u1/roles",
            data={"roles": "editor", "csrf_token": "csrf-test-token"},
        )
        assert r.status_code == 302
        assert "notice=" in r.headers["location"]
        user = app.state.user_store.update_user.await_args.args[0]
        assert user.user_id == "u1"
        assert user.roles == ["editor"]
