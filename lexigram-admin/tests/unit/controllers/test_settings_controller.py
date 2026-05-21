"""Tests for the spec-driven SettingsController."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.requests import Request

from lexigram.admin.controllers.settings import SettingsController
from lexigram.admin.settings.panel.registry import ConfigRegistry


def _mock_request(
    method: str = "GET",
    form_data: dict[str, str] | None = None,
    hx_request: bool = False,
    user: object | None = None,
) -> MagicMock:
    req = MagicMock(spec=Request)
    req.method = method
    req.headers = {"hx-request": "true"} if hx_request else {}
    req.query_params = {}
    req.path_params = {}

    async def _form() -> dict[str, str]:
        return form_data or {}

    req.form = _form
    req.state = MagicMock(user=user)
    return req


class _FakeUser:
    """AdminUser stand-in with permissions."""

    def __init__(self, permissions: frozenset[str] | None = None) -> None:
        self.permissions = permissions or frozenset()
        self.user_id = "user-1"
        self.username = "admin"


class TestSettingsController:
    """Tests for SettingsController."""

    @pytest.fixture
    def renderer(self) -> MagicMock:
        renderer = MagicMock()
        renderer.render_page = MagicMock(return_value=MagicMock(status_code=200))
        return renderer

    @pytest.fixture
    def registry(self) -> ConfigRegistry:
        return ConfigRegistry.with_defaults()

    @pytest.fixture
    def controller(
        self, renderer: MagicMock, registry: ConfigRegistry
    ) -> SettingsController:
        return SettingsController(renderer=renderer, registry=registry)

    @pytest.mark.asyncio
    async def test_index_redirects_to_first_spec(
        self, controller: SettingsController
    ) -> None:
        resp = await controller.index(_mock_request())
        assert resp.status_code == 302
        assert resp.headers["location"] == "/admin/settings/admin.branding"

    @pytest.mark.asyncio
    async def test_spec_view_renders_form(
        self, controller: SettingsController, renderer: MagicMock
    ) -> None:
        req = _mock_request()
        req.path_params = {"namespace": "admin.branding"}
        await controller.spec_view(req)
        renderer.render_page.assert_called_once()

    @pytest.mark.asyncio
    async def test_spec_view_unknown_namespace_redirects(
        self, controller: SettingsController
    ) -> None:
        req = _mock_request()
        req.path_params = {"namespace": "admin.nope"}
        resp = await controller.spec_view(req)
        assert resp.status_code == 302

    @pytest.mark.asyncio
    async def test_save_spec_persists_values(
        self, controller: SettingsController, registry: ConfigRegistry
    ) -> None:
        req = _mock_request(
            method="POST",
            form_data={
                "_csrf": "token",
                "site_name": "Acme",
                "primary_color": "#112233",
                "logo_url": "",
                "favicon_url": "",
                "dark_mode": "dark",
            },
            user=_FakeUser(),
        )
        req.path_params = {"namespace": "admin.branding"}
        resp = await controller.save_spec(req)
        assert resp.status_code == 302
        values = await registry.get_values("admin.branding", store_name="default")
        assert values["site_name"] == "Acme"
        assert values["dark_mode"] == "dark"

    @pytest.mark.asyncio
    async def test_save_spec_rejects_unknown_fields(
        self, controller: SettingsController, registry: ConfigRegistry
    ) -> None:
        req = _mock_request(
            method="POST",
            form_data={"_csrf": "token", "site_name": "Acme", "evil": "x"},
            user=_FakeUser(),
        )
        req.path_params = {"namespace": "admin.branding"}
        await controller.save_spec(req)
        values = await registry.get_values("admin.branding", store_name="default")
        assert "evil" not in values

    @pytest.mark.asyncio
    async def test_save_spec_invalid_color_falls_back(
        self, controller: SettingsController, registry: ConfigRegistry
    ) -> None:
        req = _mock_request(
            method="POST",
            form_data={
                "_csrf": "token",
                "site_name": "Acme",
                "primary_color": "blue",
                "logo_url": "",
                "favicon_url": "",
                "dark_mode": "system",
            },
            user=_FakeUser(),
        )
        req.path_params = {"namespace": "admin.branding"}
        await controller.save_spec(req)
        values = await registry.get_values("admin.branding", store_name="default")
        assert values["primary_color"] == "#6b7280"

    @pytest.mark.asyncio
    async def test_save_spec_htmx_returns_form_html(
        self, controller: SettingsController, renderer: MagicMock
    ) -> None:
        from starlette.responses import HTMLResponse

        req = _mock_request(
            method="POST",
            form_data={
                "_csrf": "token",
                "site_name": "Acme",
                "primary_color": "#112233",
                "logo_url": "",
                "favicon_url": "",
                "dark_mode": "system",
            },
            hx_request=True,
            user=_FakeUser(),
        )
        req.path_params = {"namespace": "admin.branding"}
        resp = await controller.save_spec(req)
        assert isinstance(resp, HTMLResponse)

    @pytest.mark.asyncio
    async def test_audit_logged_on_save(self, renderer: MagicMock) -> None:
        audit = AsyncMock()
        controller = SettingsController(
            renderer=renderer,
            audit_service=audit,
            registry=ConfigRegistry.with_defaults(),
        )
        req = _mock_request(
            method="POST",
            form_data={
                "_csrf": "token",
                "site_name": "Acme",
                "primary_color": "#112233",
                "logo_url": "",
                "favicon_url": "",
                "dark_mode": "system",
            },
            user=_FakeUser(),
        )
        req.path_params = {"namespace": "admin.branding"}
        await controller.save_spec(req)
        audit.log_event.assert_awaited_once()
