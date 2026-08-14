"""Tests for the observability module."""

import pytest

from lexigram.ui import (
    MetricProtocol,
    MetricsCollector,
    MetricType,
)
from lexigram.admin.ui.observability import (
    get_health_status,
    render_debug_panel,
    track_error,
    track_htmx_request,
    track_render_time,
)
from lexigram.ui.core.zones import Zones


class TestMetricType:
    """Tests for MetricType enum."""

    def test_values(self):
        assert MetricType.COUNTER.value == "counter"
        assert MetricType.HISTOGRAM.value == "histogram"
        assert MetricType.GAUGE.value == "gauge"


class TestMetric:
    """Tests for MetricProtocol dataclass."""

    def test_metric_creation(self):
        metric = MetricProtocol(
            name="requests",
            value=1.0,
            type=MetricType.COUNTER,
            labels={"resource": "users"},
        )
        assert metric.name == "requests"
        assert metric.value == 1.0
        assert metric.type == MetricType.COUNTER
        assert metric.labels == {"resource": "users"}
        assert metric.timestamp > 0


class TestMetricsCollector:
    """Tests for MetricsCollector class."""

    def test_counter_inc(self):
        collector = MetricsCollector()
        collector.inc("requests")
        assert collector.get_counter("requests") == 1

    def test_counter_multiple_inc(self):
        collector = MetricsCollector()
        collector.inc("requests", value=5)
        collector.inc("requests", value=3)
        assert collector.get_counter("requests") == 8

    def test_histogram_record(self):
        collector = MetricsCollector()
        collector.observe("latency", 0.5)
        collector.observe("latency", 1.0)
        stats = collector.get_histogram_stats("latency")
        assert stats["count"] == 2
        assert stats["avg"] == 0.75

    def test_gauge_set(self):
        collector = MetricsCollector()
        collector.set("temperature", 72.5)
        assert collector.get_gauge("temperature") == 72.5

    def test_labels(self):
        collector = MetricsCollector()
        collector.inc("requests", labels={"method": "GET"})
        collector.inc("requests", labels={"method": "POST"})
        assert collector.get_counter("requests", labels={"method": "GET"}) == 1
        assert collector.get_counter("requests", labels={"method": "POST"}) == 1

    def test_reset(self):
        collector = MetricsCollector()
        collector.inc("requests")
        collector.reset()
        assert collector.get_counter("requests") == 0


class TestTrackingFunctions:
    """Tests for tracking helper functions."""

    def setup_method(self):
        """Reset metrics before each test."""
        from unittest.mock import MagicMock
        import lexigram.admin.lib.di as di_module

        self._collector = MetricsCollector()
        mock_resolver = MagicMock()
        mock_resolver.resolve_sync.return_value = self._collector
        self._original_resolver_fn = di_module.get_admin_resolver
        di_module.get_admin_resolver = lambda context=None: mock_resolver

    def teardown_method(self):
        """Restore original resolver after each test."""
        import lexigram.admin.lib.di as di_module
        di_module.get_admin_resolver = self._original_resolver_fn

    def test_track_htmx_request(self):
        track_htmx_request("users", "#table-data", "list")

        count = self._collector.get_counter(
            "htmx_requests_total",
            labels={"resource": "users", "target": "#table-data", "action": "list"},
        )
        assert count == 1

    def test_track_render_time(self):
        track_render_time("users", "data", 42.5)

        stats = self._collector.get_histogram_stats(
            "htmx_render_seconds",
            labels={"resource": "users", "zone": "data"},
        )
        assert stats["count"] == 1
        assert stats["avg"] == pytest.approx(0.0425, rel=0.01)

    def test_track_error(self):
        track_error("users", "ValidationError", 422)

        count = self._collector.get_counter(
            "htmx_errors_total",
            labels={
                "resource": "users",
                "error_type": "ValidationError",
                "status_code": "422",
            },
        )
        assert count == 1


class TestDebugPanel:
    """Tests for debug panel rendering."""

    def test_debug_panel_hidden_without_env(self, monkeypatch):
        monkeypatch.delenv("LEX_DEBUG", raising=False)
        html = render_debug_panel()
        assert html == ""

    def test_debug_panel_shown_with_env(self, monkeypatch):
        monkeypatch.setenv("LEX_DEBUG", "1")
        html = render_debug_panel()
        assert "debug-panel" in html
        assert "Debug" in html

    def test_debug_panel_shows_zones(self, monkeypatch):
        monkeypatch.setenv("LEX_DEBUG", "1")
        zones_info = {Zones.DATA.id: True, Zones.TOOLBAR.id: False}
        html = render_debug_panel(zones_info=zones_info)
        assert Zones.DATA.id in html
        assert Zones.TOOLBAR.id in html

    def test_debug_panel_shows_timing(self, monkeypatch):
        monkeypatch.setenv("LEX_DEBUG", "1")
        html = render_debug_panel(render_time_ms=42.5)
        assert "42.50ms" in html


class TestHealthStatus:
    """Tests for health status endpoint."""

    def setup_method(self):
        """Set up fresh collector for each test."""
        from unittest.mock import MagicMock
        import lexigram.admin.lib.di as di_module

        self._collector = MetricsCollector()
        mock_resolver = MagicMock()
        mock_resolver.resolve_sync.return_value = self._collector
        self._original_resolver_fn = di_module.get_admin_resolver
        di_module.get_admin_resolver = lambda context=None: mock_resolver

    def teardown_method(self):
        """Restore original resolver after each test."""
        import lexigram.admin.lib.di as di_module
        di_module.get_admin_resolver = self._original_resolver_fn

    def test_health_status_healthy(self):
        self._collector.inc(
            "htmx_requests_total",
            labels={"resource": "test", "target": "data", "action": "list"},
        )

        status = get_health_status()
        assert status["status"] == "healthy"
        assert status["total_requests"] == 1
        assert status["total_errors"] == 0
        assert status["error_rate"] == 0

    def test_health_status_degraded(self):
        for _ in range(10):
            self._collector.inc(
                "htmx_requests_total",
                labels={"resource": "test", "target": "data", "action": "list"},
            )
        for _ in range(6):
            self._collector.inc(
                "htmx_errors_total",
                labels={
                    "resource": "test",
                    "error_type": "Error",
                    "status_code": "500",
                },
            )

        status = get_health_status()
        assert status["status"] == "degraded"
        assert status["error_rate"] > 0.05

    def test_health_status_no_requests(self):
        status = get_health_status()
        assert status["status"] == "healthy"
        assert status["total_requests"] == 0
        assert status["error_rate"] == 0
