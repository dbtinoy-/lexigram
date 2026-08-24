from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.requests import Request

from lexigram.admin.controllers.settings import SettingsController
from lexigram.admin.settings.panel import BooleanNode, ConfigSpec
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
    req.scope = {}
    return req


class _FakeUser:
    def __init__(
        self,
        permissions: frozenset[str] | None = None,
        roles: list[str] | None = None,
    ) -> None:
        self.permissions = permissions or frozenset({"admin.settings.edit"})
        self.roles = roles or []
        self.user_id = "user-1"
        self.username = "admin"


class GatedSpec(ConfigSpec):
    namespace = "admin.gated"
    label = "Gated"
    icon = "lock"
    description = ""
    required_permissions = frozenset({"admin.settings.edit"})
    flag = BooleanNode(label="Flag", default=True)


class TestSettingsControllerUpdate:
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
    async def test_save_spec_superadmin_bypasses_permission_gate(
        self, controller: SettingsController, registry: ConfigRegistry
    ) -> None:
        class GatedSpec3(ConfigSpec):
            namespace = "admin.gated3"
            label = "Gated 3"
            icon = "lock"
            description = ""
            required_permissions = frozenset({"admin.settings.edit"})
            flag = BooleanNode(label="Flag", default=True)

        registry.register_spec(GatedSpec3)
        req = _mock_request(
            method="POST",
            form_data={"_csrf": "token", "flag": "true"},
            user=_FakeUser(permissions=frozenset(), roles=["superadmin"]),
        )
        req.path_params = {"namespace": "admin.gated3"}
        resp = await controller.save_spec(req)
        assert resp.status_code == 302
        values = await registry.get_values("admin.gated3", store_name="default")
        assert values["flag"] is True

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

    def test_render_toast_escapes_message(self) -> None:
        controller = SettingsController(
            renderer=MagicMock(), registry=ConfigRegistry.with_defaults()
        )
        html = controller._render_toast('<img src=x onerror="alert(1)">', "success")
        assert 'class="toast toast-success"' in html
        assert "<img" not in html
        assert '<img src=x onerror="alert(1)">' not in html
        assert '&lt;img src=x onerror="alert(1)"&gt;' in html

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

    @pytest.mark.asyncio
    async def test_save_spec_int_and_bool_fields_not_flagged_invalid(
        self, renderer: MagicMock
    ) -> None:
        audit = AsyncMock()
        controller = SettingsController(
            renderer=renderer,
            audit_service=audit,
            registry=ConfigRegistry.with_defaults(),
        )
        req = _mock_request(
            method="POST",
            form_data={
                "csrf_token": "token",
                "enabled": "true",
                "default_ttl": "120",
            },
            user=_FakeUser(),
        )
        req.path_params = {"namespace": "admin.cache"}
        await controller.save_spec(req)
        call_kwargs = audit.log_event.await_args
        assert call_kwargs is not None
        assert call_kwargs.kwargs["metadata"]["invalid"] == []

    @pytest.mark.asyncio
    async def test_save_spec_normalizes_on_to_true_for_boolean(
        self, renderer: MagicMock
    ) -> None:
        audit = AsyncMock()
        registry = ConfigRegistry.with_defaults()
        controller = SettingsController(
            renderer=renderer,
            audit_service=audit,
            registry=registry,
        )
        req = _mock_request(
            method="POST",
            form_data={
                "csrf_token": "token",
                "enabled": "on",
                "default_ttl": "120",
            },
            user=_FakeUser(),
        )
        req.path_params = {"namespace": "admin.cache"}
        await controller.save_spec(req)
        call_kwargs = audit.log_event.await_args
        assert call_kwargs is not None
        assert call_kwargs.kwargs["metadata"]["invalid"] == []
        values = await registry.get_values("admin.cache")
        assert values["enabled"] is True

    @pytest.mark.asyncio
    async def test_save_spec_persists_false_for_unchecked_boolean(
        self, renderer: MagicMock
    ) -> None:
        audit = AsyncMock()
        registry = ConfigRegistry.with_defaults()
        controller = SettingsController(
            renderer=renderer,
            audit_service=audit,
            registry=registry,
        )
        req = _mock_request(
            method="POST",
            form_data={
                "csrf_token": "token",
                "enabled": "false",
                "default_ttl": "120",
            },
            user=_FakeUser(),
        )
        req.path_params = {"namespace": "admin.cache"}
        await controller.save_spec(req)
        values = await registry.get_values("admin.cache")
        assert values["enabled"] is False

    @pytest.mark.asyncio
    async def test_save_spec_checked_toggle_wins_over_hidden_false(
        self, renderer: MagicMock
    ) -> None:
        from starlette.datastructures import FormData

        audit = AsyncMock()
        registry = ConfigRegistry.with_defaults()
        controller = SettingsController(
            renderer=renderer,
            audit_service=audit,
            registry=registry,
        )
        req = _mock_request(
            method="POST",
            form_data=None,
            user=_FakeUser(),
        )

        async def _form() -> FormData:
            return FormData(
                [("enabled", "on"), ("enabled", "false"), ("default_ttl", "120")]
            )

        req.form = _form
        req.path_params = {"namespace": "admin.cache"}
        await controller.save_spec(req)
        values = await registry.get_values("admin.cache")
        assert values["enabled"] is True
        assert values["default_ttl"] == 120

    @pytest.mark.asyncio
    async def test_save_spec_permission_denied(self, renderer: MagicMock) -> None:
        from starlette.responses import RedirectResponse

        registry = ConfigRegistry.with_defaults()
        registry.register_spec(GatedSpec)

        audit = AsyncMock()
        controller = SettingsController(
            renderer=renderer,
            audit_service=audit,
            registry=registry,
        )
        req = _mock_request(
            method="POST",
            form_data={"flag": "true"},
            user=_FakeUser(permissions=frozenset({"admin.other"})),
        )
        req.path_params = {"namespace": "admin.gated"}
        resp = await controller.save_spec(req)
        assert isinstance(resp, RedirectResponse)
        audit.log_event.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_save_spec_bound_spec_requires_permission(
        self, renderer: MagicMock
    ) -> None:
        from starlette.responses import RedirectResponse

        registry = ConfigRegistry.with_defaults()

        audit = AsyncMock()
        controller = SettingsController(
            renderer=renderer,
            audit_service=audit,
            registry=registry,
        )
        req = _mock_request(
            method="POST",
            form_data={"csp": "default-src 'self'", "hsts_max_age": "3600"},
            user=_FakeUser(permissions=frozenset({"admin.other"})),
        )
        req.path_params = {"namespace": "admin.security"}
        resp = await controller.save_spec(req)
        assert isinstance(resp, RedirectResponse)
        audit.log_event.assert_awaited_once()
        values = await registry.get_values("admin.security")
        assert values.get("hsts_max_age", 0) != 3600
