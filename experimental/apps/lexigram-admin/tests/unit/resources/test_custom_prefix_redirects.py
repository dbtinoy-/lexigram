"""Custom admin prefix must flow into redirects built by the resource pipeline."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

from starlette.applications import Starlette

from lexigram.admin.config import AdminConfig
from lexigram.admin.core.routing import AdminRouter
from lexigram.admin.resources.handler import ResourceHandler


def _mock_resource(name: str = "users") -> MagicMock:
    resource = MagicMock()
    resource.name = name
    resource.model = None
    resource.relations = []
    resource._data_source = None
    return resource


async def _drain(handler: ResourceHandler) -> dict[str, Any]:
    scope: dict[str, Any] = {"type": "http", "method": "GET", "headers": []}
    await handler(scope, AsyncMock(), AsyncMock())
    return scope


class TestResourceHandlerScope:
    async def test_handler_sets_admin_prefix_from_config(self) -> None:
        config = AdminConfig(prefix="/console")
        handler = ResourceHandler(config=config, name="users", action="list")
        handler._registry.handle = AsyncMock()  # type: ignore[method-assign]

        scope = await _drain(handler)

        assert scope["admin_prefix"] == "/console"
        assert scope["admin_resource_prefix"] == "users"

    async def test_handler_defaults_prefix_when_unset(self) -> None:
        config = AdminConfig()
        handler = ResourceHandler(config=config, name="users", action="list")
        handler._registry.handle = AsyncMock()  # type: ignore[method-assign]

        scope = await _drain(handler)

        assert scope["admin_prefix"] == "/admin"


class TestMountedAppState:
    def test_mounted_app_state_exposes_configured_prefix(self) -> None:
        config = AdminConfig(prefix="/console")
        router = AdminRouter(config=config)
        app = Starlette()
        admin_app = router.mount(app)  # type: ignore[func-returns-value]
        assert admin_app is not None
        assert admin_app.state.admin_prefix == "/console"

    def test_mounted_app_state_defaults_to_admin(self) -> None:
        config = AdminConfig()
        router = AdminRouter(config=config)
        app = Starlette()
        admin_app = router.mount(app)  # type: ignore[func-returns-value]
        assert admin_app is not None
        assert admin_app.state.admin_prefix == "/admin"


class TestRedirectTargets:
    def test_edit_redirect_uses_custom_prefix(self) -> None:
        from lexigram.admin.resources.urls import admin_url

        assert admin_url("/console", "users", "1/edit") == "/console/users/1/edit"

    def test_list_redirect_uses_custom_prefix(self) -> None:
        from lexigram.admin.resources.urls import admin_url

        assert admin_url("/console", "users") == "/console/users"
