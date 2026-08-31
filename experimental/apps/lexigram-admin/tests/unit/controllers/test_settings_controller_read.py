from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.requests import Request

from lexigram.admin.auth.types import AdminSecurityEventType
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


class UngatedSpec(ConfigSpec):
    namespace = "admin.ungated"
    label = "Ungated"
    icon = "lock"
    description = ""
    flag = BooleanNode(label="Flag", default=True)


class TestSettingsControllerRead:
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
        resp = await controller.index(_mock_request(user=_FakeUser()))
        assert resp.status_code == 302
        assert resp.headers["location"] == "/admin/settings/admin.branding"

    @pytest.mark.asyncio
    async def test_spec_view_renders_form(
        self, controller: SettingsController, renderer: MagicMock
    ) -> None:
        req = _mock_request(user=_FakeUser())
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
    async def test_index_superadmin_sees_gated_specs_without_permissions(
        self,
        controller: SettingsController,
        registry: ConfigRegistry,
    ) -> None:
        class GatedSpec2(ConfigSpec):
            namespace = "admin.gated2"
            label = "Gated 2"
            icon = "lock"
            description = ""
            required_permissions = frozenset({"admin.settings.edit"})
            flag = BooleanNode(label="Flag", default=True)

        registry.register_spec(GatedSpec2)
        req = _mock_request(
            user=_FakeUser(permissions=frozenset(), roles=["superadmin"]),
        )
        _, visible = controller._build_categories(req)
        assert any(spec.namespace == "admin.gated2" for spec in visible)


class TestSettingsSpecViewPermissionGate:
    @pytest.fixture
    def renderer(self) -> MagicMock:
        renderer = MagicMock()
        renderer.render_page = MagicMock(return_value=MagicMock(status_code=200))
        return renderer

    def _make_controller(
        self, renderer: MagicMock, audit: MagicMock | None = None
    ) -> tuple[SettingsController, ConfigRegistry]:
        registry = ConfigRegistry.with_defaults()
        registry.register_spec(GatedSpec)
        controller = SettingsController(
            renderer=renderer,
            audit_service=audit,
            registry=registry,
        )
        return controller, registry

    @pytest.mark.asyncio
    async def test_spec_view_denied_without_permission(
        self, renderer: MagicMock
    ) -> None:
        audit = MagicMock()
        audit.log_event = AsyncMock()
        controller, registry = self._make_controller(renderer, audit)
        registry.get_values = AsyncMock()
        req = _mock_request(user=_FakeUser(permissions=frozenset({"admin.other"})))
        req.path_params = {"namespace": "admin.gated"}
        resp = await controller.spec_view(req)
        assert resp.status_code == 302
        assert resp.headers["location"] == "/admin/settings"
        registry.get_values.assert_not_awaited()
        audit.log_event.assert_awaited_once()
        call_kwargs = audit.log_event.await_args
        assert call_kwargs is not None
        assert (
            call_kwargs.kwargs["event_type"] == AdminSecurityEventType.PERMISSION_DENIED
        )
        assert call_kwargs.kwargs["success"] is False
        assert call_kwargs.kwargs["metadata"] == {"reason": "permission_denied"}

    @pytest.mark.asyncio
    async def test_spec_view_allowed_with_permission(self, renderer: MagicMock) -> None:
        controller, _ = self._make_controller(renderer)
        req = _mock_request(user=_FakeUser())
        req.path_params = {"namespace": "admin.gated"}
        await controller.spec_view(req)
        renderer.render_page.assert_called_once()

    @pytest.mark.asyncio
    async def test_spec_view_allows_read_only_permission_without_edit_access(
        self, renderer: MagicMock
    ) -> None:
        class ViewableSpec(ConfigSpec):
            namespace = "admin.viewable"
            label = "Viewable"
            read_permissions = frozenset({"admin.settings.view"})
            edit_permissions = frozenset({"admin.settings.edit"})
            flag = BooleanNode(label="Flag", default=True)

        registry = ConfigRegistry.with_defaults()
        registry.register_spec(ViewableSpec)
        controller = SettingsController(renderer=renderer, registry=registry)
        user = SimpleNamespace(
            permissions=frozenset({"admin.settings.view"}),
            roles=[],
            user_id="viewer",
        )
        req = _mock_request(user=user)
        req.path_params = {"namespace": "admin.viewable"}

        await controller.spec_view(req)

        assert controller._can_access_spec(req, ViewableSpec, "read")
        assert not controller._can_access_spec(req, ViewableSpec, "edit")
        renderer.render_page.assert_called_once()

    @pytest.mark.asyncio
    async def test_read_only_permission_cannot_save(
        self, renderer: MagicMock
    ) -> None:
        class ViewableSpec(ConfigSpec):
            namespace = "admin.viewable-save"
            label = "Viewable"
            read_permissions = frozenset({"admin.settings.view"})
            edit_permissions = frozenset({"admin.settings.edit"})
            flag = BooleanNode(label="Flag", default=True)

        registry = ConfigRegistry.with_defaults()
        registry.register_spec(ViewableSpec)
        controller = SettingsController(renderer=renderer, registry=registry)
        user = SimpleNamespace(
            permissions=frozenset({"admin.settings.view"}),
            roles=[],
            user_id="viewer",
        )
        req = _mock_request(method="POST", user=user)
        req.path_params = {"namespace": "admin.viewable-save"}

        response = await controller.save_spec(req)

        assert response.status_code == 302
        assert response.headers["location"] == "/admin/settings/admin.viewable-save"

    @pytest.mark.asyncio
    async def test_spec_view_superadmin_bypasses_permission_gate(
        self, renderer: MagicMock
    ) -> None:
        controller, _ = self._make_controller(renderer)
        req = _mock_request(
            user=_FakeUser(
                permissions=frozenset({"admin.other"}), roles=["superadmin"]
            ),
        )
        req.path_params = {"namespace": "admin.gated"}
        await controller.spec_view(req)
        renderer.render_page.assert_called_once()

    @pytest.mark.asyncio
    async def test_spec_view_ungated_spec_renders_without_permissions(
        self, renderer: MagicMock
    ) -> None:
        registry = ConfigRegistry.with_defaults()
        registry.register_spec(UngatedSpec)
        controller = SettingsController(renderer=renderer, registry=registry)
        req = _mock_request(user=_FakeUser(permissions=frozenset({"admin.other"})))
        req.path_params = {"namespace": "admin.ungated"}
        await controller.spec_view(req)
        renderer.render_page.assert_called_once()

    @pytest.mark.asyncio
    async def test_spec_view_denied_when_audit_fails(self, renderer: MagicMock) -> None:
        audit = MagicMock()
        audit.log_event = AsyncMock(side_effect=RuntimeError("audit down"))
        controller, _ = self._make_controller(renderer, audit)
        req = _mock_request(user=_FakeUser(permissions=frozenset({"admin.other"})))
        req.path_params = {"namespace": "admin.gated"}
        resp = await controller.spec_view(req)
        assert resp.status_code == 302
        assert resp.headers["location"] == "/admin/settings"


class TestRenderedForm:
    def test_form_renders_real_html(self) -> None:
        from lexigram.admin.settings.panel import BrandingSpec
        from lexigram.admin.settings.panel.ui import ConfigDashboardUI
        from lexigram.ui.core.base import render_to_string

        ui = ConfigDashboardUI()
        html = render_to_string(
            ui.render_config_form(
                spec=BrandingSpec.to_dict(),
                values={},
                action="/admin/settings/admin.branding",
                csrf_token="tok123",
            )
        )
        assert "<form" in html
        assert 'name="csrf_token"' in html
        assert 'value="tok123"' in html
