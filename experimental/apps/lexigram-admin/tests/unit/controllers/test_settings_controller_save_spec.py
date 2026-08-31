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
        req = _mock_request(
            method="POST", form_data={"api_key": "sk-new"}, user=_FakeUser()
        )
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
            raise AssertionError(
                "resolve_tenant_id should not be called for global specs"
            )

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

    def test_store_name_falls_back_to_default_when_spec_store_unregistered(
        self,
    ) -> None:
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


class _MultiForm:
    """Small FormData stand-in that preserves duplicate field names."""

    def __init__(self, *items: tuple[str, str]) -> None:
        self._items = list(items)

    def multi_items(self):
        return iter(self._items)


class TestSettingsFormDataAndValidation:
    """Real browser form semantics must be safe and recoverable."""

    @pytest.mark.asyncio
    async def test_checked_boolean_wins_over_hidden_false_fallback(self) -> None:
        registry = ConfigRegistry.with_defaults()
        await registry.save_values(
            "admin.cache", {"enabled": "false"}, store_name="default"
        )
        renderer = MagicMock()
        renderer.render_page = MagicMock(return_value=MagicMock(status_code=200))
        controller = SettingsController(renderer=renderer, registry=registry)
        req = _mock_request(user=_FakeUser())
        req.method = "POST"
        req.path_params = {"namespace": "admin.cache"}
        req.scope["admin_form_data"] = _MultiForm(
            ("enabled", "true"),
            ("enabled", "false"),
            ("default_ttl", "120"),
        )

        await controller.save_spec(req)

        values = await registry.get_values("admin.cache")
        assert values["enabled"] is True
        assert values["default_ttl"] == 120

    @pytest.mark.asyncio
    async def test_invalid_value_is_not_saved_and_is_rendered_inline(self) -> None:
        registry = ConfigRegistry.with_defaults()
        renderer = MagicMock()
        controller = SettingsController(renderer=renderer, registry=registry)
        req = _mock_request(
            method="POST",
            form_data={"enabled": "true", "default_ttl": "-1"},
            hx_request=True,
            user=_FakeUser(),
        )
        req.path_params = {"namespace": "admin.cache"}

        response = await controller.save_spec(req)

        # HTMX must receive a 200 response so its default response policy
        # swaps the recoverable error fragment into the form.
        assert response.status_code == 200
        html = response.body.decode()
        assert "Default TTL (seconds) must be at least 0." in html
        assert 'value="-1"' in html
        values = await registry.get_values("admin.cache")
        assert values["default_ttl"] == 60
