"""E2E HTTP tests for the resource-backed admin roles pages.

Replaces the legacy RbacController e2e suite: routes now go through the
generic resource handler stack (``ResourceHandler`` → action handlers).
Covers the RBAC delete guard end-to-end — protected roles (system and
super-admin) cannot be deleted, custom roles can.
"""

from __future__ import annotations

from typing import Any

from httpx import ASGITransport, AsyncClient
import pytest
from starlette.applications import Starlette
from starlette.routing import Route

from lexigram.admin.config import AdminConfig
from lexigram.contracts.auth import RoleDefinition
from lexigram.admin.resources.handler import ResourceHandler
from lexigram.admin.resources.roles import RolesResource


class _RolesDataSource:
    """In-memory roles store (superadmin + system + custom role)."""

    def __init__(self) -> None:
        self.roles: dict[str, RoleDefinition] = {
            "superadmin": RoleDefinition(
                name="superadmin",
                description="Built-in super admin",
                is_system=True,
            ),
            "admin": RoleDefinition(name="admin", is_system=True),
            "editor": RoleDefinition(
                name="editor",
                permissions=["users.view", "users.update"],
            ),
        }

    async def find_one(self, item_id: Any) -> RoleDefinition | None:
        """Fetch a role by name."""
        return self.roles.get(str(item_id))

    async def find_many(self, query: Any) -> Any:
        """Return all roles."""
        from lexigram.admin.data import QueryResult

        return QueryResult(items=list(self.roles.values()), total=len(self.roles))

    async def count(self, query: Any) -> int:
        """Count roles."""
        return len(self.roles)

    async def delete(self, item_id: Any) -> bool:
        """Delete a role by name."""
        key = str(item_id)
        if key not in self.roles:
            return False
        del self.roles[key]
        return True


def _make_app() -> Starlette:
    """Build a Starlette app with the resource routes for roles."""
    resource = RolesResource()
    resource._data_source = _RolesDataSource()
    resources = {"roles": resource}
    config = AdminConfig(prefix="/admin", title="Test Admin")

    def _handler(action: str) -> ResourceHandler:
        return ResourceHandler(config, "roles", action, resources=resources)

    return Starlette(
        routes=[
            Route(
                "/admin/roles",
                _handler("list"),
                name="admin_roles_list",
            ),
            Route(
                "/admin/roles/{id}/delete",
                _handler("delete"),
                name="admin_roles_delete",
                methods=["POST"],
            ),
            Route(
                "/admin/roles/{id}/delete-confirm",
                _handler("delete-confirm"),
                name="admin_roles_delete_confirm",
                methods=["GET"],
            ),
        ]
    )


@pytest.mark.asyncio
async def test_roles_list_renders_resource_table() -> None:
    """The roles index renders through the resource list handler."""
    app = _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/admin/roles")
        assert response.status_code == 200
        assert "editor" in response.text or "superadmin" in response.text


@pytest.mark.asyncio
async def test_super_admin_role_delete_is_blocked() -> None:
    """The super-admin role survives a delete attempt."""
    app = _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/admin/roles/superadmin/delete")
        assert response.status_code == 409
        assert "cannot be deleted" in response.text


@pytest.mark.asyncio
async def test_system_role_delete_is_blocked() -> None:
    """System roles survive a delete attempt."""
    app = _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/admin/roles/admin/delete")
        assert response.status_code == 409


@pytest.mark.asyncio
async def test_custom_role_delete_succeeds() -> None:
    """A custom role is deleted and the store is updated."""
    app = _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/admin/roles/editor/delete",
            headers={"HX-Request": "true"},
        )
        assert response.status_code == 200
        assert "HX-Trigger" in response.headers
        assert "HX-Redirect" in response.headers
        assert await app.routes[1].endpoint._resources["roles"]._data_source.find_one(
            "editor"
        ) is None


@pytest.mark.asyncio
async def test_delete_confirm_renders_for_known_role() -> None:
    """The delete confirmation slide-over renders for an existing role."""
    app = _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/admin/roles/editor/delete-confirm")
        assert response.status_code == 200
        assert "Delete" in response.text
