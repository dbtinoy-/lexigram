"""Tests for the spec-driven SettingsController."""

from __future__ import annotations

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
    """AdminUser stand-in with permissions."""

    def __init__(
        self,
        permissions: frozenset[str] | None = None,
        roles: list[str] | None = None,
    ) -> None:
        self.permissions = permissions or frozenset({"admin.settings.edit"})
        self.roles = roles or []
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
        """Toggle + hidden-false submit both; the 'on' value must win."""
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


class GatedSpec(ConfigSpec):
    """Spec requiring a permission."""

    namespace = "admin.gated"
    label = "Gated"
    icon = "lock"
    description = ""
    required_permissions = frozenset({"admin.settings.edit"})
    flag = BooleanNode(label="Flag", default=True)


class UngatedSpec(ConfigSpec):
    """Spec without a required permission."""

    namespace = "admin.ungated"
    label = "Ungated"
    icon = "lock"
    description = ""
    flag = BooleanNode(label="Flag", default=True)


class TestSettingsSpecViewPermissionGate:
    """spec_view GET requires the spec's required_permissions."""

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
    """Tests for actual rendered form output."""

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


class TestSaveSpecReadonlyEnforcement:
    """save_spec must never persist a readonly field, even via direct POST."""

    @pytest.mark.asyncio
    async def test_readonly_field_in_post_is_ignored_and_audited(self) -> None:
        from lexigram.admin.settings.panel.nodes import ConfigSpec, StringNode

        class _ReadonlySpec(ConfigSpec):
            namespace = "admin.readonly_post_test"
            label = "Readonly Post Test"
            icon = "lock"
            description = ""
            locked = StringNode(label="Locked", default="original", readonly=True)

        registry = ConfigRegistry()
        registry._specs["admin.readonly_post_test"] = _ReadonlySpec
        audit = AsyncMock()
        renderer = MagicMock()
        renderer.render_page = MagicMock(return_value=MagicMock(status_code=200))
        controller = SettingsController(
            renderer=renderer, audit_service=audit, registry=registry
        )

        req = _mock_request(
            method="POST", form_data={"locked": "hacked"}, user=_FakeUser()
        )
        req.path_params = {"namespace": "admin.readonly_post_test"}
        await controller.save_spec(req)

        values = await registry.get_values("admin.readonly_post_test")
        assert values["locked"] == "original"
        _, kwargs = audit.log_event.call_args
        assert kwargs["metadata"]["ignored_readonly"] == ["locked"]


class TestSaveSpecSecretHandling:
    """Blank secret submissions must not overwrite the stored value."""

    @pytest.mark.asyncio
    async def test_blank_secret_submission_leaves_stored_value_unchanged(self) -> None:
        from lexigram.admin.settings.panel.nodes import ConfigSpec, SecretNode

        class _SecretSpec(ConfigSpec):
            namespace = "admin.secret_test"
            label = "Secret Test"
            icon = "key"
            description = ""
            api_key = SecretNode(label="API Key", default="")

        registry = ConfigRegistry()
        registry._specs["admin.secret_test"] = _SecretSpec
        await registry.save_values("admin.secret_test", {"api_key": "sk-original"})

        renderer = MagicMock()
        renderer.render_page = MagicMock(return_value=MagicMock(status_code=200))
        controller = SettingsController(renderer=renderer, registry=registry)
        req = _mock_request(method="POST", form_data={"api_key": ""}, user=_FakeUser())
        req.path_params = {"namespace": "admin.secret_test"}
        await controller.save_spec(req)

        values = await registry.get_values("admin.secret_test")
        assert values["api_key"] == "sk-original"

    @pytest.mark.asyncio
    async def test_non_blank_secret_submission_overwrites(self) -> None:
        from lexigram.admin.settings.panel.nodes import ConfigSpec, SecretNode

        class _SecretSpec2(ConfigSpec):
            namespace = "admin.secret_test2"
            label = "Secret Test 2"
            icon = "key"
            description = ""
            api_key = SecretNode(label="API Key", default="")

        registry = ConfigRegistry()
        registry._specs["admin.secret_test2"] = _SecretSpec2
        await registry.save_values("admin.secret_test2", {"api_key": "sk-original"})

        renderer = MagicMock()
        renderer.render_page = MagicMock(return_value=MagicMock(status_code=200))
        controller = SettingsController(renderer=renderer, registry=registry)
        req = _mock_request(method="POST", form_data={"api_key": "sk-new"}, user=_FakeUser())
        req.path_params = {"namespace": "admin.secret_test2"}
        await controller.save_spec(req)

        values = await registry.get_values("admin.secret_test2")
        assert values["api_key"] == "sk-new"


class TestSettingsCsrfSessionScope:
    """The rendered form token must bind to the same session id the CSRF
    middleware validates against (csrf_session_id first, then admin_user_id)."""

    @staticmethod
    def _controller() -> SettingsController:
        from lexigram.admin.auth.services.csrf_service import AdminCsrfService

        return SettingsController(
            renderer=MagicMock(),
            csrf_service=AdminCsrfService(secret="test-secret"),
            registry=ConfigRegistry.with_defaults(),
        )

    def test_token_valid_against_middleware_session_selection(self) -> None:
        controller = self._controller()
        req = _mock_request(user=_FakeUser())
        req.session = {
            "csrf_session_id": "stale-pre-login",
            "admin_user_id": "user-1",
        }
        token = controller._get_csrf_token(req)
        assert token is not None

        # Mirror of middleware/csrf.py session-id resolution.
        session_id = req.session.get("csrf_session_id") or req.session.get(
            "admin_user_id", "anonymous"
        )
        assert controller._csrf_service.validate_token(session_id, token)  # type: ignore[union-attr]

    def test_token_valid_against_plain_authenticated_session(self) -> None:
        controller = self._controller()
        req = _mock_request(user=_FakeUser())
        req.session = {"admin_user_id": "user-1"}
        token = controller._get_csrf_token(req)
        assert token is not None
        assert controller._csrf_service.validate_token("user-1", token)  # type: ignore[union-attr]


class TestDynamicCategories:
    @pytest.mark.asyncio
    async def test_categories_are_grouped_by_package_source(self) -> None:
        registry = ConfigRegistry.with_defaults()
        renderer = MagicMock()
        renderer.render_page = MagicMock(return_value=MagicMock(status_code=200))
        controller = SettingsController(renderer=renderer, registry=registry)
        req = _mock_request(user=_FakeUser())
        categories, visible = controller._build_categories(req)
        assert len(categories) == 1
        assert categories[0].name == "built-in"
        assert len(visible) == 9


class TestTenantScopedSettings:
    @pytest.mark.asyncio
    async def test_tenant_scoped_spec_resolves_tenant_id(self, monkeypatch) -> None:
        from lexigram.admin.settings.panel import BrandingSpec

        registry = ConfigRegistry.with_defaults()
        renderer = MagicMock()
        renderer.render_page = MagicMock(return_value=MagicMock(status_code=200))
        controller = SettingsController(renderer=renderer, registry=registry)

        async def _fake_resolve(request, *, default):
            return "tenant-42"

        monkeypatch.setattr(
            "lexigram.admin.controllers.settings.resolve_tenant_id", _fake_resolve
        )

        called_with = {}
        original_get_values = registry.get_values

        async def _spy_get_values(namespace, store_name="default", tenant_id=None):
            called_with["tenant_id"] = tenant_id
            return await original_get_values(namespace, store_name, tenant_id=tenant_id)

        registry.get_values = _spy_get_values

        req = _mock_request(user=_FakeUser())
        req.path_params = {"namespace": "admin.branding"}
        await controller.spec_view(req)

        assert called_with["tenant_id"] == "tenant-42"
        assert BrandingSpec.scope == "tenant"

    @pytest.mark.asyncio
    async def test_global_scoped_spec_passes_no_tenant_id(self, monkeypatch) -> None:
        registry = ConfigRegistry.with_defaults()
        renderer = MagicMock()
        renderer.render_page = MagicMock(return_value=MagicMock(status_code=200))
        controller = SettingsController(renderer=renderer, registry=registry)

        async def _fail_resolve(request, *, default):
            raise AssertionError("resolve_tenant_id should not be called for global specs")

        monkeypatch.setattr(
            "lexigram.admin.controllers.settings.resolve_tenant_id", _fail_resolve
        )

        req = _mock_request(user=_FakeUser())
        req.path_params = {"namespace": "admin.cache"}
        await controller.spec_view(req)


class TestStoreNameResolution:
    def test_store_name_defaults_to_db_when_registered(self) -> None:
        from lexigram.admin.settings.panel.registry import MemoryStore

        registry = ConfigRegistry.with_defaults()
        registry.register_store("db", MemoryStore())
        renderer = MagicMock()
        controller = SettingsController(renderer=renderer, registry=registry)

        from lexigram.admin.settings.panel import CacheSpec

        assert controller._store_name(CacheSpec) == "db"

    def test_store_name_falls_back_to_default_when_spec_store_unregistered(self) -> None:
        registry = ConfigRegistry.with_defaults()
        renderer = MagicMock()
        controller = SettingsController(renderer=renderer, registry=registry)

        from lexigram.admin.settings.panel import CacheSpec

        assert controller._store_name(CacheSpec) == "default"

    def test_env_scoped_spec_resolves_to_env_store(self) -> None:
        from lexigram.admin.settings.panel.nodes import ConfigSpec

        class _EnvSpec(ConfigSpec):
            namespace = "test.env_spec"
            label = "Env Spec"
            icon = "server"
            description = ""
            store_name = "env"

        registry = ConfigRegistry.with_defaults()
        renderer = MagicMock()
        controller = SettingsController(renderer=renderer, registry=registry)
        assert controller._store_name(_EnvSpec) == "env"
