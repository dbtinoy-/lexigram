"""Tests for WidgetController routing logic."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.routing import Route

from lexigram.admin.auth.types import AdminSecurityEventType
from lexigram.admin.controllers.widgets import WidgetController
from lexigram.contracts.admin.health_payload import HealthCheckPayload
from lexigram.contracts.admin.types import (
    AdminHealthDefinition,
    DashboardWidgetDefinition,
    WidgetKind,
    WidgetViewModel,
)
from lexigram.contracts.admin.widget_content import MessageContent
from lexigram.contracts.core.health import HealthStatus
from lexigram.result import Err, Ok


class TestWidgetController:
    @pytest.fixture
    def mock_registry(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_contributor(self) -> MagicMock:
        return MagicMock()

    @pytest.mark.asyncio
    async def test_returns_200_with_error_card_when_contributor_not_found(
        self, mock_registry: MagicMock
    ) -> None:
        mock_registry.get.return_value = None
        controller = WidgetController(registry=mock_registry)
        mock_request = MagicMock()
        mock_request.query_params = {}
        response = await controller.render_widget(
            request=mock_request,
            contributor_id="nonexistent",
            widget_name="some_widget",
        )
        assert response.status_code == 200
        assert b"widget-error-card" in response.body
        assert b"Contributor" in response.body

    @pytest.mark.asyncio
    async def test_returns_html_on_ok_result(
        self, mock_registry: MagicMock, mock_contributor: MagicMock
    ) -> None:
        mock_registry.get.return_value = mock_contributor
        mock_contributor.render_widget = AsyncMock(
            return_value=Ok(WidgetViewModel(content=MessageContent(text="ok")))
        )
        controller = WidgetController(registry=mock_registry)
        mock_request = MagicMock()
        mock_request.query_params = {}
        response = await controller.render_widget(
            request=mock_request,
            contributor_id="sql",
            widget_name="pool_utilization",
        )
        assert response.status_code == 200
        assert b"ok" in response.body

    @pytest.mark.asyncio
    async def test_returns_200_with_error_card_on_widget_not_found(
        self, mock_registry: MagicMock, mock_contributor: MagicMock
    ) -> None:
        from lexigram.contracts.admin.errors import WidgetNotFoundError

        mock_registry.get.return_value = mock_contributor
        mock_contributor.render_widget = AsyncMock(
            return_value=Err(WidgetNotFoundError("sql", "unknown_widget"))
        )
        controller = WidgetController(registry=mock_registry)
        mock_request = MagicMock()
        mock_request.query_params = {}
        response = await controller.render_widget(
            request=mock_request,
            contributor_id="sql",
            widget_name="unknown_widget",
        )
        assert response.status_code == 200
        assert b"widget-error-card" in response.body

    @pytest.mark.asyncio
    async def test_returns_200_with_error_card_on_domain_error(
        self, mock_registry: MagicMock, mock_contributor: MagicMock
    ) -> None:
        from lexigram.contracts.admin.errors import AdminError

        mock_registry.get.return_value = mock_contributor
        mock_contributor.render_widget = AsyncMock(
            return_value=Err(AdminError("data unavailable"))
        )
        controller = WidgetController(registry=mock_registry)
        mock_request = MagicMock()
        mock_request.query_params = {}
        response = await controller.render_widget(
            request=mock_request,
            contributor_id="sql",
            widget_name="pool_utilization",
        )
        assert response.status_code == 200
        assert b"widget-error-card" in response.body


class TestWidgetControllerGetRoutes:
    """Tests for WidgetController.get_routes() method."""

    @pytest.fixture
    def mock_registry(self) -> MagicMock:
        return MagicMock()

    def test_get_routes_returns_list(self, mock_registry: MagicMock) -> None:
        """Test that get_routes returns a list."""
        controller = WidgetController(registry=mock_registry)
        routes = controller.get_routes()
        assert isinstance(routes, list)

    def test_get_routes_returns_starlette_routes(
        self, mock_registry: MagicMock
    ) -> None:
        """Test that get_routes returns Starlette Route objects."""
        controller = WidgetController(registry=mock_registry)
        routes = controller.get_routes()
        for route in routes:
            assert isinstance(route, Route)

    def test_get_routes_includes_widget_route(self, mock_registry: MagicMock) -> None:
        """Test that widget route is included."""
        controller = WidgetController(registry=mock_registry)
        routes = controller.get_routes()
        paths = [r.path for r in routes]
        assert any("/{contributor_id}/widgets/{widget_name}" in p for p in paths)

    def test_get_routes_includes_health_route(self, mock_registry: MagicMock) -> None:
        """Test that health check route is included."""
        controller = WidgetController(registry=mock_registry)
        routes = controller.get_routes()
        paths = [r.path for r in routes]
        assert any("/{contributor_id}/health/{check_name}" in p for p in paths)

    def test_get_routes_path_no_admin_prefix(self, mock_registry: MagicMock) -> None:
        """Test that route paths do not have duplicate /admin prefix.

        Routes are mounted at /admin via Mount(), so get_routes() should
        return paths like /{contributor_id}/widgets/{widget_name}, not
        /admin/{contributor_id}/widgets/{widget_name}.
        """
        controller = WidgetController(registry=mock_registry)
        routes = controller.get_routes()
        for route in routes:
            assert not route.path.startswith("/admin"), (
                f"Route path '{route.path}' should not include /admin prefix - "
                "the Mount() provides that."
            )

    def test_get_routes_has_methods(self, mock_registry: MagicMock) -> None:
        """Test that routes have correct HTTP methods."""
        controller = WidgetController(registry=mock_registry)
        routes = controller.get_routes()
        paths_to_methods = {r.path: r.methods for r in routes}
        widget_route = next(p for p in paths_to_methods if "widgets" in p)
        assert "GET" in paths_to_methods[widget_route]

    def test_get_routes_endpoint_is_callable(self, mock_registry: MagicMock) -> None:
        """Test that route endpoints are callable."""
        controller = WidgetController(registry=mock_registry)
        routes = controller.get_routes()
        for route in routes:
            assert callable(route.endpoint)

    def test_get_routes_endpoint_signature(self, mock_registry: MagicMock) -> None:
        """Test that endpoints accept request parameter."""
        controller = WidgetController(registry=mock_registry)
        routes = controller.get_routes()
        for route in routes:
            import inspect

            sig = inspect.signature(route.endpoint)
            assert "request" in sig.parameters


class TestWidgetControllerPermissionGate:
    """Mutating widget endpoints require admin.settings.edit."""

    @pytest.fixture
    def user_with_perm(self) -> MagicMock:
        user = MagicMock()
        user.permissions = frozenset({"admin.settings.edit"})
        return user

    @pytest.fixture
    def user_without_perm(self) -> MagicMock:
        user = MagicMock()
        user.permissions = frozenset({"admin.users.view"})
        return user

    def _make_controller(self, audit: MagicMock | None = None) -> WidgetController:
        registry = MagicMock()
        return WidgetController(registry=registry, audit_service=audit)

    def _make_request(self, user: MagicMock) -> MagicMock:
        request = MagicMock()
        state = MagicMock()
        state.user = user
        request.state = state
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        request.headers = {"user-agent": "test-agent"}
        return request

    @pytest.mark.asyncio
    async def test_save_widget_config_denied_without_permission(
        self, user_without_perm: MagicMock
    ) -> None:
        audit = MagicMock()
        audit.log_event = AsyncMock()
        controller = self._make_controller(audit)
        response = await controller.save_widget_config(
            self._make_request(user_without_perm)
        )
        assert response.status_code == 403
        audit.log_event.assert_awaited_once_with(
            event_type=AdminSecurityEventType.PERMISSION_DENIED,
            ip_address="127.0.0.1",
            user_agent="test-agent",
            success=False,
            metadata={
                "reason": "permission_denied",
                "route": "save_widget_config",
            },
        )

    @pytest.mark.asyncio
    async def test_save_widget_config_allowed_with_permission(
        self, user_with_perm: MagicMock
    ) -> None:
        audit = MagicMock()
        audit.log_event = AsyncMock()
        controller = self._make_controller(audit)
        request = self._make_request(user_with_perm)
        request.form = AsyncMock(return_value={"widget_name": "w", "enabled": "on"})
        controller._settings_service = None
        response = await controller.save_widget_config(request)
        assert response.status_code == 204
        assert audit.log_event.await_count == 1

    @pytest.mark.asyncio
    async def test_reorder_widgets_denied_without_permission(
        self, user_without_perm: MagicMock
    ) -> None:
        audit = MagicMock()
        audit.log_event = AsyncMock()
        controller = self._make_controller(audit)
        response = await controller.reorder_widgets(
            self._make_request(user_without_perm)
        )
        assert response.status_code == 403
        audit.log_event.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_save_all_widget_configs_denied_without_permission(
        self, user_without_perm: MagicMock
    ) -> None:
        audit = MagicMock()
        audit.log_event = AsyncMock()
        controller = self._make_controller(audit)
        response = await controller.save_all_widget_configs(
            self._make_request(user_without_perm)
        )
        assert response.status_code == 403
        audit.log_event.assert_awaited_once()


class TestWidgetConfigPopupPermissionGate:
    """widget_config_popup / customize_all_widgets GETs require edit permission."""

    @pytest.fixture
    def user_with_perm(self) -> MagicMock:
        user = MagicMock()
        user.permissions = frozenset({"admin.settings.edit"})
        return user

    @pytest.fixture
    def user_without_perm(self) -> MagicMock:
        user = MagicMock()
        user.permissions = frozenset({"admin.users.view"})
        return user

    @pytest.fixture
    def superadmin(self) -> MagicMock:
        user = MagicMock()
        user.permissions = frozenset()
        user.roles = ["superadmin"]
        return user

    def _make_request(self, user: MagicMock) -> MagicMock:
        request = MagicMock()
        state = MagicMock()
        state.user = user
        request.state = state
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        request.headers = {"user-agent": "test-agent"}
        return request

    def _make_controller(
        self, audit: MagicMock | None = None
    ) -> tuple[WidgetController, MagicMock]:
        registry = MagicMock()
        contributor = MagicMock()
        widget_def = DashboardWidgetDefinition(
            name="pool_utilization",
            title="Pool Utilization",
            contributor="sql",
            render_endpoint="/admin/sql/widgets/pool_utilization",
            view_kind=WidgetKind.MESSAGE,
        )
        contributor.get_dashboard_widgets.return_value = [widget_def]
        contributor.get_widget_config_schema = MagicMock(return_value=[])
        registry.get_all.return_value = [contributor]
        settings = MagicMock()
        settings.get_widget_prefs = AsyncMock(
            return_value={"enabled": [], "configs": {}}
        )
        controller = WidgetController(registry=registry, audit_service=audit)
        controller._settings_service = settings
        return controller, settings

    @pytest.mark.asyncio
    async def test_widget_config_popup_denied_without_permission(
        self, user_without_perm: MagicMock
    ) -> None:
        audit = MagicMock()
        audit.log_event = AsyncMock()
        controller, settings = self._make_controller(audit)
        response = await controller.widget_config_popup(
            self._make_request(user_without_perm), name="pool_utilization"
        )
        assert response.status_code == 403
        settings.get_widget_prefs.assert_not_awaited()
        audit.log_event.assert_awaited_once_with(
            event_type=AdminSecurityEventType.PERMISSION_DENIED,
            ip_address="127.0.0.1",
            user_agent="test-agent",
            success=False,
            metadata={
                "reason": "permission_denied",
                "route": "widget_config_popup",
            },
        )

    @pytest.mark.asyncio
    async def test_widget_config_popup_allowed_with_permission(
        self, user_with_perm: MagicMock
    ) -> None:
        controller, settings = self._make_controller()
        response = await controller.widget_config_popup(
            self._make_request(user_with_perm), name="pool_utilization"
        )
        assert response.status_code == 200
        settings.get_widget_prefs.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_widget_config_popup_superadmin_bypasses(
        self, superadmin: MagicMock
    ) -> None:
        controller, settings = self._make_controller()
        response = await controller.widget_config_popup(
            self._make_request(superadmin), name="pool_utilization"
        )
        assert response.status_code == 200
        settings.get_widget_prefs.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_widget_config_popup_unknown_widget_404s_before_gate(
        self, user_without_perm: MagicMock
    ) -> None:
        audit = MagicMock()
        audit.log_event = AsyncMock()
        registry = MagicMock()
        registry.get_all.return_value = []
        controller = WidgetController(registry=registry, audit_service=audit)
        response = await controller.widget_config_popup(
            self._make_request(user_without_perm), name="unknown_widget"
        )
        assert response.status_code == 404
        audit.log_event.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_widget_config_popup_denied_when_audit_fails(
        self, user_without_perm: MagicMock
    ) -> None:
        audit = MagicMock()
        audit.log_event = AsyncMock(side_effect=RuntimeError("audit down"))
        controller, _ = self._make_controller(audit)
        response = await controller.widget_config_popup(
            self._make_request(user_without_perm), name="pool_utilization"
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_customize_all_widgets_denied_without_permission(
        self, user_without_perm: MagicMock
    ) -> None:
        audit = MagicMock()
        audit.log_event = AsyncMock()
        controller, settings = self._make_controller(audit)
        response = await controller.customize_all_widgets(
            self._make_request(user_without_perm)
        )
        assert response.status_code == 403
        settings.get_widget_prefs.assert_not_awaited()
        audit.log_event.assert_awaited_once_with(
            event_type=AdminSecurityEventType.PERMISSION_DENIED,
            ip_address="127.0.0.1",
            user_agent="test-agent",
            success=False,
            metadata={
                "reason": "permission_denied",
                "route": "customize_all_widgets",
            },
        )

    @pytest.mark.asyncio
    async def test_customize_all_widgets_allowed_with_permission(
        self, user_with_perm: MagicMock
    ) -> None:
        controller, settings = self._make_controller()
        response = await controller.customize_all_widgets(
            self._make_request(user_with_perm)
        )
        assert response.status_code == 200
        settings.get_widget_prefs.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_customize_all_widgets_superadmin_bypasses(
        self, superadmin: MagicMock
    ) -> None:
        controller, settings = self._make_controller()
        response = await controller.customize_all_widgets(
            self._make_request(superadmin)
        )
        assert response.status_code == 200
        settings.get_widget_prefs.assert_awaited_once()


def _user_with_permissions(*permissions: str) -> MagicMock:
    """Build a user mock with the given permission set and no roles."""
    user = MagicMock()
    user.permissions = frozenset(permissions)
    user.roles = frozenset()
    return user


def _request_for(user: MagicMock) -> MagicMock:
    """Build a request mock carrying the given user on state."""
    request = MagicMock()
    request.query_params = {}
    state = MagicMock()
    state.user = user
    request.state = state
    return request


class TestWidgetControllerWidgetPermissionGate:
    """Declared widget permissions gate render_widget dispatch."""

    WIDGET_NAME = "widget_count"

    @pytest.fixture
    def widget_def(self) -> DashboardWidgetDefinition:
        return DashboardWidgetDefinition(
            name=self.WIDGET_NAME,
            title="Widget Count",
            contributor="sql",
            render_endpoint="/admin/sql/widgets/widget_count",
            view_kind=WidgetKind.MESSAGE,
            permission="governance.read",
        )

    def _make_controller(
        self, widget_def: DashboardWidgetDefinition
    ) -> tuple[WidgetController, MagicMock]:
        registry = MagicMock()
        contributor = MagicMock()
        contributor.get_dashboard_widgets.return_value = [widget_def]
        contributor.render_widget = AsyncMock(
            return_value=Ok(WidgetViewModel(content=MessageContent(text="ok")))
        )
        registry.get.return_value = contributor
        return WidgetController(registry=registry), contributor

    @pytest.mark.asyncio
    async def test_render_widget_denies_when_user_lacks_declared_permission(
        self, widget_def: DashboardWidgetDefinition
    ) -> None:
        controller, contributor = self._make_controller(widget_def)
        response = await controller.render_widget(
            request=_request_for(_user_with_permissions("admin.users.view")),
            contributor_id="sql",
            widget_name=self.WIDGET_NAME,
        )
        assert response.status_code == 200
        assert b"widget-error-card" in response.body
        assert b"permission" in response.body.lower()
        contributor.render_widget.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_render_widget_allows_when_user_has_declared_permission(
        self, widget_def: DashboardWidgetDefinition
    ) -> None:
        controller, contributor = self._make_controller(widget_def)
        response = await controller.render_widget(
            request=_request_for(
                _user_with_permissions("admin.users.view", "governance.read")
            ),
            contributor_id="sql",
            widget_name=self.WIDGET_NAME,
        )
        assert response.status_code == 200
        assert b"ok" in response.body
        contributor.render_widget.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_render_widget_allows_when_widget_declares_no_permission(
        self, widget_def: DashboardWidgetDefinition
    ) -> None:
        widget_def = DashboardWidgetDefinition(
            name=self.WIDGET_NAME,
            title="Widget Count",
            contributor="sql",
            render_endpoint="/admin/sql/widgets/widget_count",
            view_kind=WidgetKind.MESSAGE,
        )
        controller, contributor = self._make_controller(widget_def)
        response = await controller.render_widget(
            request=_request_for(_user_with_permissions()),
            contributor_id="sql",
            widget_name=self.WIDGET_NAME,
        )
        assert response.status_code == 200
        assert b"ok" in response.body
        contributor.render_widget.assert_awaited_once()


class TestWidgetControllerHealthPermissionGate:
    """Declared health permissions gate render_health_check dispatch."""

    CHECK_NAME = "governance.billing"

    @pytest.fixture
    def health_def(self) -> AdminHealthDefinition:
        return AdminHealthDefinition(
            name=self.CHECK_NAME,
            contributor="ai-governance",
            component="Billing",
            permission="governance.read",
        )

    def _make_controller(
        self, health_def: AdminHealthDefinition
    ) -> tuple[WidgetController, MagicMock]:
        registry = MagicMock()
        contributor = MagicMock()
        contributor.get_health_definitions.return_value = [health_def]
        contributor.render_health_check = AsyncMock(
            return_value=Ok(
                HealthCheckPayload(
                    status=HealthStatus.HEALTHY,
                    component="Billing",
                    detail="available",
                )
            )
        )
        registry.get.return_value = contributor
        return WidgetController(registry=registry), contributor

    @pytest.mark.asyncio
    async def test_render_health_permission_denied_when_user_lacks_declared_permission(
        self, health_def: AdminHealthDefinition
    ) -> None:
        controller, contributor = self._make_controller(health_def)
        response = await controller.render_health_check(
            request=_request_for(_user_with_permissions("admin.users.view")),
            contributor_id="ai-governance",
            check_name=self.CHECK_NAME,
        )
        assert response.status_code == 403
        contributor.render_health_check.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_render_health_permission_allowed_when_user_has_declared_permission(
        self, health_def: AdminHealthDefinition
    ) -> None:
        controller, contributor = self._make_controller(health_def)
        response = await controller.render_health_check(
            request=_request_for(
                _user_with_permissions("admin.users.view", "governance.read")
            ),
            contributor_id="ai-governance",
            check_name=self.CHECK_NAME,
        )
        assert response.status_code == 200
        assert b"health-check-badge" in response.body
        assert b"healthy" in response.body
        contributor.render_health_check.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_render_health_permission_allowed_when_no_permission_declared(
        self, health_def: AdminHealthDefinition
    ) -> None:
        health_def = AdminHealthDefinition(
            name=self.CHECK_NAME,
            contributor="ai-governance",
            component="Billing",
        )
        controller, contributor = self._make_controller(health_def)
        response = await controller.render_health_check(
            request=_request_for(_user_with_permissions()),
            contributor_id="ai-governance",
            check_name=self.CHECK_NAME,
        )
        assert response.status_code == 200
        assert b"health-check-badge" in response.body
        contributor.render_health_check.assert_awaited_once()
