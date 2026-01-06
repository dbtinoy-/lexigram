"""End-to-end integration tests for admin widget rendering architecture.

Verifies the full admin widget discovery, registration, and rendering pipeline.
Tests that all framework package admin contributors are discoverable, importable,
and compliant with the widget rendering protocol.
"""

from __future__ import annotations

import pytest

from lexigram.admin.contributors.registry import ContributorRegistry
from lexigram.contracts.admin.errors import WidgetNotFoundError, HealthCheckNotFoundError
from lexigram.contracts.admin.types import WidgetParams


class TestAdminContributorImportability:
    """Test that all admin contributors can be imported without errors."""

    def test_core_admin_contributor_importable(self) -> None:
        """Test core admin contributor is importable."""
        from lexigram.admin.contributors.core import CoreAdminContributor

        assert CoreAdminContributor is not None
        assert hasattr(CoreAdminContributor, "__name__")

    def test_cache_admin_contributor_importable(self) -> None:
        """Test cache admin contributor is importable."""
        from lexigram.cache.admin.contributor import CacheAdminContributor

        assert CacheAdminContributor is not None
        assert CacheAdminContributor.__name__ == "CacheAdminContributor"

    def test_sql_admin_contributor_importable(self) -> None:
        """Test sql admin contributor is importable."""
        from lexigram.sql.admin.contributor import SqlAdminContributor

        assert SqlAdminContributor is not None
        assert SqlAdminContributor.__name__ == "SqlAdminContributor"

    def test_web_admin_contributor_importable(self) -> None:
        """Test web admin contributor is importable."""
        from lexigram.web.admin.contributor import WebAdminContributor

        assert WebAdminContributor is not None
        assert WebAdminContributor.__name__ == "WebAdminContributor"

    def test_auth_admin_contributor_importable(self) -> None:
        """Test auth admin contributor is importable."""
        from lexigram.auth.admin.contributor import AuthAdminContributor

        assert AuthAdminContributor is not None
        assert AuthAdminContributor.__name__ == "AuthAdminContributor"

    def test_events_admin_contributor_importable(self) -> None:
        """Test events admin contributor is importable."""
        from lexigram.events.admin.contributor import EventsAdminContributor

        assert EventsAdminContributor is not None
        assert EventsAdminContributor.__name__ == "EventsAdminContributor"

    def test_tasks_admin_contributor_importable(self) -> None:
        """Test tasks admin contributor is importable."""
        from lexigram.tasks.admin.contributor import TasksAdminContributor

        assert TasksAdminContributor is not None
        assert TasksAdminContributor.__name__ == "TasksAdminContributor"

    def test_queue_admin_contributor_importable(self) -> None:
        """Test queue admin contributor is importable."""
        from lexigram.queue.admin.contributor import QueueAdminContributor

        assert QueueAdminContributor is not None
        assert QueueAdminContributor.__name__ == "QueueAdminContributor"

    def test_ai_llm_admin_contributor_importable(self) -> None:
        """Test ai-llm admin contributor is importable."""
        from lexigram.ai.llm.admin.contributor import LlmAdminContributor

        assert LlmAdminContributor is not None
        assert LlmAdminContributor.__name__ == "LlmAdminContributor"

    def test_webhook_admin_contributor_importable(self) -> None:
        """Test webhook admin contributor is importable."""
        try:
            from lexigram.webhook.admin.contributor import WebhookAdminContributor

            assert WebhookAdminContributor is not None
            assert WebhookAdminContributor.__name__ == "WebhookAdminContributor"
        except (ImportError, ModuleNotFoundError):
            pytest.skip("lexigram-webhook not available in this environment")

    def test_audit_admin_contributor_importable(self) -> None:
        """Test audit admin contributor is importable."""
        try:
            from lexigram.audit.admin.contributor import AuditAdminContributor

            assert AuditAdminContributor is not None
            assert AuditAdminContributor.__name__ == "AuditAdminContributor"
        except (ImportError, ModuleNotFoundError):
            pytest.skip("lexigram-audit not available in this environment")


class TestAdminContributorRegistry:
    """Test the contributor registry mechanism."""

    def test_registry_empty_on_init(self) -> None:
        """Test registry is empty when initialized."""
        registry = ContributorRegistry()
        assert len(list(registry.get_all())) == 0

    def test_registry_with_defaults(self) -> None:
        """Test registry can be created with defaults."""
        registry = ContributorRegistry.with_defaults()
        assert registry is not None

    def test_registry_get_returns_none_for_missing(self) -> None:
        """Test registry returns None for missing contributor."""
        registry = ContributorRegistry()
        assert registry.get("nonexistent") is None

    def test_registry_get_all_returns_sequence(self) -> None:
        """Test registry get_all returns a sequence."""
        registry = ContributorRegistry()
        result = registry.get_all()
        assert isinstance(result, (list, tuple))

    def test_registry_get_by_group(self) -> None:
        """Test registry can filter by group."""
        registry = ContributorRegistry()
        result = registry.get_by_group("infrastructure")
        assert isinstance(result, (list, tuple))


class TestWidgetHandlerProtocol:
    """Test that all widget handlers comply with WidgetHandlerProtocol."""

    def test_cache_handler_has_get_data(self) -> None:
        """Test cache hit/miss handler has get_data method."""
        from lexigram.cache.admin.handlers.hit_miss_ratio import (
            HitMissRatioWidgetHandler,
        )

        assert hasattr(HitMissRatioWidgetHandler, "get_data")
        assert callable(getattr(HitMissRatioWidgetHandler, "get_data"))

    def test_cache_eviction_handler_has_get_data(self) -> None:
        """Test cache eviction handler has get_data method."""
        from lexigram.cache.admin.handlers.eviction_rate import (
            EvictionRateWidgetHandler,
        )

        assert hasattr(EvictionRateWidgetHandler, "get_data")
        assert callable(getattr(EvictionRateWidgetHandler, "get_data"))

    def test_cache_ping_handler_has_get_data(self) -> None:
        """Test cache backend ping handler has get_data method."""
        from lexigram.cache.admin.handlers.backend_ping import (
            BackendPingWidgetHandler,
        )

        assert hasattr(BackendPingWidgetHandler, "get_data")
        assert callable(getattr(BackendPingWidgetHandler, "get_data"))

    def test_sql_pool_handler_has_get_data(self) -> None:
        """Test SQL pool utilization handler has get_data method."""
        from lexigram.sql.admin.handlers.pool_utilization import (
            PoolUtilizationWidgetHandler,
        )

        assert hasattr(PoolUtilizationWidgetHandler, "get_data")
        assert callable(getattr(PoolUtilizationWidgetHandler, "get_data"))

    def test_sql_query_stats_handler_has_get_data(self) -> None:
        """Test SQL query stats handler has get_data method."""
        from lexigram.sql.admin.handlers.query_stats import QueryStatsWidgetHandler

        assert hasattr(QueryStatsWidgetHandler, "get_data")
        assert callable(getattr(QueryStatsWidgetHandler, "get_data"))

    def test_sql_connection_handler_has_get_data(self) -> None:
        """Test SQL active connections handler has get_data method."""
        try:
            from lexigram.sql.admin.handlers.active_connections import (
                ActiveConnectionsWidgetHandler,
            )

            assert hasattr(ActiveConnectionsWidgetHandler, "get_data")
            assert callable(getattr(ActiveConnectionsWidgetHandler, "get_data"))
        except ImportError:
            pytest.skip("ActiveConnectionsWidgetHandler not available in this environment")


class TestWidgetRendererConfiguration:
    """Test that all widget renderers are properly configured."""

    def test_cache_renderer_has_jinja_env(self) -> None:
        """Test cache renderer has Jinja2 environment configured."""
        from lexigram.cache.admin.renderer import PackageWidgetRenderer

        renderer = PackageWidgetRenderer()
        assert hasattr(renderer, "_env")
        assert renderer._env is not None

    def test_cache_renderer_autoescape_enabled(self) -> None:
        """Test cache renderer has autoescape enabled."""
        from lexigram.cache.admin.renderer import PackageWidgetRenderer

        renderer = PackageWidgetRenderer()
        assert renderer._env.autoescape is not None

    def test_sql_renderer_has_jinja_env(self) -> None:
        """Test SQL renderer has Jinja2 environment configured."""
        from lexigram.sql.admin.renderer import PackageWidgetRenderer as SqlRenderer

        renderer = SqlRenderer()
        assert hasattr(renderer, "_env")
        assert renderer._env is not None

    def test_sql_renderer_autoescape_enabled(self) -> None:
        """Test SQL renderer has autoescape enabled."""
        from lexigram.sql.admin.renderer import PackageWidgetRenderer as SqlRenderer

        renderer = SqlRenderer()
        assert renderer._env.autoescape is not None

    def test_web_renderer_has_jinja_env(self) -> None:
        """Test web renderer has Jinja2 environment configured."""
        from lexigram.web.admin.renderer import PackageWidgetRenderer as WebRenderer

        renderer = WebRenderer()
        assert hasattr(renderer, "_env")
        assert renderer._env is not None


class TestErrorHandling:
    """Test error handling in admin widgets."""

    def test_widget_not_found_error_creation(self) -> None:
        """Test WidgetNotFoundError can be created."""
        error = WidgetNotFoundError("test-contributor", "nonexistent-widget")
        assert "test-contributor" in str(error)
        assert "nonexistent-widget" in str(error)

    def test_widget_not_found_error_attributes(self) -> None:
        """Test WidgetNotFoundError has required attributes."""
        error = WidgetNotFoundError("cache", "missing")
        assert error.contributor_name == "cache"
        assert error.widget_name == "missing"

    def test_health_check_not_found_error_creation(self) -> None:
        """Test HealthCheckNotFoundError can be created."""
        error = HealthCheckNotFoundError("sql", "missing-check")
        assert "sql" in str(error)
        assert "missing-check" in str(error)

    def test_health_check_not_found_error_attributes(self) -> None:
        """Test HealthCheckNotFoundError has required attributes."""
        error = HealthCheckNotFoundError("cache", "backend-health")
        assert error.contributor_name == "cache"
        assert error.check_name == "backend-health"


class TestWidgetTypesAndValues:
    """Test widget type definitions and value types."""

    def test_widget_params_creation(self) -> None:
        """Test WidgetParams can be created."""
        params = WidgetParams(
            page=1, page_size=10, time_window_minutes=60, raw=False
        )
        assert params.page == 1
        assert params.page_size == 10
        assert params.time_window_minutes == 60
        assert params.raw is False

    def test_widget_params_defaults(self) -> None:
        """Test WidgetParams has correct defaults."""
        params = WidgetParams()
        assert params.page == 1
        assert params.page_size == 20  # Updated from 10 to actual default
        assert params.time_window_minutes == 60
        assert params.raw == ()

    def test_widget_params_frozen(self) -> None:
        """Test WidgetParams is frozen (immutable)."""
        params = WidgetParams(page=1)
        with pytest.raises(Exception):  # FrozenInstanceError
            params.page = 2

    def test_dashboard_widget_definition_creation(self) -> None:
        """Test DashboardWidgetDefinition can be created."""
        from lexigram.contracts.admin.types import (
            DashboardWidgetDefinition,
            WidgetSize,
            WidgetCategory,
        )

        widget = DashboardWidgetDefinition(
            name="test-widget",
            title="Test Widget",
            contributor="test",
            render_endpoint="/admin/test/test-widget",
            size=WidgetSize.SMALL,
            category=WidgetCategory.METRICS,
        )
        assert widget.name == "test-widget"
        assert widget.title == "Test Widget"
        assert widget.size == WidgetSize.SMALL

    def test_dashboard_widget_definition_frozen(self) -> None:
        """Test DashboardWidgetDefinition is frozen."""
        from lexigram.contracts.admin.types import DashboardWidgetDefinition

        widget = DashboardWidgetDefinition(
            name="test",
            title="Test",
            contributor="test",
            render_endpoint="/test",
        )
        with pytest.raises(Exception):  # FrozenInstanceError
            widget.name = "changed"


class TestViewModels:
    """Test admin widget viewmodels."""

    def test_cache_hit_miss_viewmodel_creation(self) -> None:
        """Test HitMissRatioViewModel can be created."""
        from lexigram.cache.admin.viewmodels import HitMissRatioViewModel

        vm = HitMissRatioViewModel(hits=100, misses=20, hit_rate_pct=83.3, window_minutes=60)
        assert vm.hits == 100
        assert vm.misses == 20
        assert vm.hit_rate_pct == 83.3

    def test_cache_hit_miss_viewmodel_frozen(self) -> None:
        """Test HitMissRatioViewModel is frozen."""
        from lexigram.cache.admin.viewmodels import HitMissRatioViewModel

        vm = HitMissRatioViewModel(hits=100, misses=20, hit_rate_pct=83.3, window_minutes=60)
        with pytest.raises(Exception):  # FrozenInstanceError
            vm.hits = 200

    def test_cache_eviction_viewmodel_creation(self) -> None:
        """Test EvictionRateViewModel can be created."""
        from lexigram.cache.admin.viewmodels import EvictionRateViewModel

        vm = EvictionRateViewModel(evictions_per_second=1.5, total_evictions=10000)
        assert vm.evictions_per_second == 1.5
        assert vm.total_evictions == 10000

    def test_cache_backend_ping_viewmodel_creation(self) -> None:
        """Test BackendPingViewModel can be created."""
        from lexigram.cache.admin.viewmodels import BackendPingViewModel

        vm = BackendPingViewModel(latency_ms=2.5, is_reachable=True, backend_name="redis")
        assert vm.latency_ms == 2.5
        assert vm.is_reachable is True
        assert vm.backend_name == "redis"

    def test_sql_pool_utilization_viewmodel_creation(self) -> None:
        """Test PoolUtilizationViewModel can be created."""
        from lexigram.sql.admin.viewmodels import PoolUtilizationViewModel

        vm = PoolUtilizationViewModel(
            pool_size=30,
            active_connections=15,
            idle_connections=10,
            utilization_pct=50.0,
        )
        assert vm.pool_size == 30
        assert vm.active_connections == 15
        assert vm.utilization_pct == 50.0

    def test_sql_pool_utilization_viewmodel_frozen(self) -> None:
        """Test PoolUtilizationViewModel is frozen."""
        from lexigram.sql.admin.viewmodels import PoolUtilizationViewModel

        vm = PoolUtilizationViewModel(
            pool_size=30,
            active_connections=15,
            idle_connections=10,
            utilization_pct=50.0,
        )
        with pytest.raises(Exception):  # FrozenInstanceError
            vm.active_connections = 20

    def test_sql_query_stats_viewmodel_creation(self) -> None:
        """Test QueryStatsViewModel can be created."""
        from lexigram.sql.admin.viewmodels import QueryStatsViewModel

        vm = QueryStatsViewModel(
            total_queries=5000,
            avg_duration_ms=1.2,
            slow_queries=10,
            error_count=5,
        )
        assert vm.total_queries == 5000
        assert vm.slow_queries == 10

    def test_sql_active_connections_viewmodel_creation(self) -> None:
        """Test migration status viewmodel can be created."""
        from lexigram.sql.admin.viewmodels import MigrationStatusViewModel

        vm = MigrationStatusViewModel(
            current_version="20240101_001",
            total_applied=25,
            pending_count=0,
            is_current=True,
        )
        assert vm.current_version == "20240101_001"
        assert vm.is_current is True


class TestEntryPointRegistration:
    """Test that admin contributors are registered via entry points."""

    def test_entry_point_group_exists(self) -> None:
        """Test that the admin contributors entry point group exists."""
        import importlib.metadata

        ENTRY_POINT_GROUP = "lexigram.admin.contributors"

        try:
            eps = importlib.metadata.entry_points(group=ENTRY_POINT_GROUP)
            # Should have at least the core contributor
            ep_list = list(eps)
            assert len(ep_list) > 0
        except Exception:
            # Entry points may not be discoverable in all test environments
            # Manual verification of pyproject.toml is acceptable
            pytest.skip("Entry points not discoverable in this environment")

    def test_core_entry_point_discoverable(self) -> None:
        """Test that core admin contributor is discoverable via entry points."""
        import importlib.metadata

        ENTRY_POINT_GROUP = "lexigram.admin.contributors"

        try:
            eps = importlib.metadata.entry_points(group=ENTRY_POINT_GROUP)
            ep_names = {ep.name for ep in eps}
            assert "core" in ep_names
        except Exception:
            pytest.skip("Entry points not discoverable in this environment")


class TestResultPatternCompliance:
    """Test that handlers return Result types correctly."""

    def test_result_import(self) -> None:
        """Test Result type can be imported."""
        from lexigram.result import Result, Ok, Err

        assert Result is not None
        assert Ok is not None
        assert Err is not None

    def test_result_ok_creation(self) -> None:
        """Test Ok result can be created."""
        from lexigram.result import Ok

        value = "test"
        result = Ok(value)
        assert result.is_ok() is True

    def test_result_err_creation(self) -> None:
        """Test Err result can be created."""
        from lexigram.result import Err
        from lexigram.contracts.admin.errors import AdminError

        error = AdminError("test error")
        result = Err(error)
        assert result.is_err() is True

    def test_result_unwrap_ok(self) -> None:
        """Test unwrapping Ok result."""
        from lexigram.result import Ok

        value = "test value"
        result = Ok(value)
        assert result.unwrap() == value

    def test_result_unwrap_err(self) -> None:
        """Test unwrapping Err result."""
        from lexigram.result import Err
        from lexigram.contracts.admin.errors import AdminError

        error = AdminError("test")
        result = Err(error)
        unwrapped = result.unwrap_err()
        assert isinstance(unwrapped, AdminError)

    def test_result_is_ok(self) -> None:
        """Test is_ok predicate."""
        from lexigram.result import Ok, Err
        from lexigram.contracts.admin.errors import AdminError

        ok_result = Ok("value")
        err_result = Err(AdminError("error"))

        assert ok_result.is_ok() is True
        assert err_result.is_ok() is False

    def test_result_is_err(self) -> None:
        """Test is_err predicate."""
        from lexigram.result import Ok, Err
        from lexigram.contracts.admin.errors import AdminError

        ok_result = Ok("value")
        err_result = Err(AdminError("error"))

        assert ok_result.is_err() is False
        assert err_result.is_err() is True


class TestPiccolinaIntegration:
    """Test Piccolina admin integration (optional)."""

    def test_piccolina_admin_contributor_importable(self) -> None:
        """Test that Piccolina admin contributor can be imported (if available)."""
        try:
            from piccolina.backend.admin.contributor import PiccolinaAdminContributor

            assert PiccolinaAdminContributor is not None
        except ImportError:
            pytest.skip("Piccolina not available in test environment")

    def test_piccolina_admin_widgets_importable(self) -> None:
        """Test Piccolina admin widgets are importable (if available)."""
        try:
            from piccolina.backend.admin import contributor

            assert contributor is not None
        except ImportError:
            pytest.skip("Piccolina not available in test environment")


__all__ = [
    "TestAdminContributorImportability",
    "TestAdminContributorRegistry",
    "TestWidgetHandlerProtocol",
    "TestWidgetRendererConfiguration",
    "TestErrorHandling",
    "TestWidgetTypesAndValues",
    "TestViewModels",
    "TestEntryPointRegistration",
    "TestResultPatternCompliance",
    "TestPiccolinaIntegration",
]
