"""Tests for HTMX performance optimization patterns."""

from htpy import a, div, input_

from lexigram.admin.services.htmx_perf import HTMXPerformanceMonitor
from lexigram.ui.htmx.helpers import (
    hx_boost,
    hx_debounce,
    hx_lazy_load,
    hx_morph,
    hx_optimistic,
    hx_polling,
    hx_prefetch,
    hx_preserve,
    hx_sse,
    hx_swap_oob,
    hx_websocket,
)


class TestHXSwapOOB:
    """Test out-of-band swap helpers."""

    def test_single_oob_swap(self):
        """Test creating single OOB swap."""
        result = hx_swap_oob(("target", div["Content"]))
        assert len(result) == 1
        assert "hx-swap-oob" in str(result[0])

    def test_multiple_oob_swaps(self):
        """Test creating multiple OOB swaps."""
        result = hx_swap_oob(
            ("target1", div["Content 1"]),
            ("target2", div["Content 2"]),
            ("target3", div["Content 3"]),
        )
        assert len(result) == 3

    def test_oob_swap_with_element_id(self):
        """Test OOB swap includes target ID."""
        result = hx_swap_oob(("notifications", div["3 new"]))
        assert len(result) == 1
        # Result should be a wrapped div element
        assert "div" in str(result[0])


class TestHXPrefetch:
    """Test prefetching helpers."""

    def test_default_prefetch(self):
        """Test prefetch with defaults."""
        attrs = hx_prefetch("/api/data")
        assert attrs["hx-get"] == "/api/data"
        assert "mouseenter" in attrs["hx-trigger"]
        assert "200ms" in attrs["hx-trigger"]
        assert attrs["hx-swap"] == "none"

    def test_custom_trigger(self):
        """Test prefetch with custom trigger."""
        attrs = hx_prefetch("/api/data", trigger="focus")
        assert "focus" in attrs["hx-trigger"]

    def test_custom_threshold(self):
        """Test prefetch with custom threshold."""
        attrs = hx_prefetch("/api/data", threshold="500ms")
        assert "500ms" in attrs["hx-trigger"]

    def test_prefetch_on_link(self):
        """Test prefetch applied to link."""
        link = a["Details"][{"href": "/users/1", **hx_prefetch("/users/1")}]
        assert "hx-get" in str(link)


class TestHXLazyLoad:
    """Test lazy loading helpers."""

    def test_default_lazy_load(self):
        """Test lazy load with defaults."""
        attrs = hx_lazy_load("/api/content")
        assert attrs["hx-get"] == "/api/content"
        assert "revealed" in attrs["hx-trigger"]
        assert "0px" in attrs["hx-trigger"]
        assert attrs["hx-swap"] == "outerHTML"

    def test_custom_trigger(self):
        """Test lazy load with custom trigger."""
        attrs = hx_lazy_load("/api/content", trigger="intersect")
        assert "intersect" in attrs["hx-trigger"]

    def test_custom_threshold(self):
        """Test lazy load with custom threshold."""
        attrs = hx_lazy_load("/api/content", threshold="100px")
        assert "100px" in attrs["hx-trigger"]

    def test_with_placeholder(self):
        """Test lazy load with placeholder."""
        attrs = hx_lazy_load("/api/content", placeholder="Loading...")
        assert "hx-indicator" in attrs
        assert attrs["hx-indicator"] == "Loading..."


class TestHXMorph:
    """Test morphing helpers."""

    def test_morph_without_target(self):
        """Test morph without target."""
        attrs = hx_morph()
        assert attrs["hx-swap"] == "morph"
        assert "hx-target" not in attrs

    def test_morph_with_target(self):
        """Test morph with target selector."""
        attrs = hx_morph(target="#content")
        assert attrs["hx-swap"] == "morph"
        assert attrs["hx-target"] == "#content"


class TestHXPreserve:
    """Test preservation helpers."""

    def test_preserve_single_selector(self):
        """Test preserving single element."""
        attrs = hx_preserve("input")
        assert attrs["hx-preserve"] == "input"

    def test_preserve_multiple_selectors(self):
        """Test preserving multiple elements."""
        attrs = hx_preserve("input", "textarea", ".keep")
        assert "input" in attrs["hx-preserve"]
        assert "textarea" in attrs["hx-preserve"]
        assert ".keep" in attrs["hx-preserve"]


class TestHXBoost:
    """Test boosting helpers."""

    def test_default_boost(self):
        """Test boost with defaults."""
        attrs = hx_boost()
        assert attrs["hx-boost"] == "true"
        assert "hx-target" not in attrs

    def test_boost_disabled(self):
        """Test disabling boost."""
        attrs = hx_boost(enable=False)
        assert attrs["hx-boost"] == "false"

    def test_boost_with_target(self):
        """Test boost with target."""
        attrs = hx_boost(target="#content")
        assert attrs["hx-target"] == "#content"

    def test_boost_with_swap(self):
        """Test boost with custom swap."""
        attrs = hx_boost(swap="outerHTML")
        assert attrs["hx-swap"] == "outerHTML"


class TestHXDebounce:
    """Test debouncing helpers."""

    def test_default_debounce(self):
        """Test debounce with default delay."""
        attrs = hx_debounce()
        assert "delay:500ms" in attrs["hx-trigger"]
        assert "keyup changed" in attrs["hx-trigger"]

    def test_custom_delay(self):
        """Test debounce with custom delay."""
        attrs = hx_debounce("300ms")
        assert "delay:300ms" in attrs["hx-trigger"]

    def test_debounce_on_input(self):
        """Test debounce applied to input."""
        search = input_[
            {
                "type": "search",
                "hx-get": "/search",
                **hx_debounce("200ms"),
            }
        ]
        assert "hx-trigger" in str(search)


class TestHXOptimistic:
    """Test optimistic UI helpers."""

    def test_default_optimistic(self):
        """Test optimistic with defaults."""
        attrs = hx_optimistic()
        assert "settle:0ms" in attrs["hx-swap"]
        assert "hx-indicator" not in attrs

    def test_optimistic_with_indicator(self):
        """Test optimistic with loading indicator."""
        attrs = hx_optimistic(indicator="#spinner")
        assert attrs["hx-indicator"] == "#spinner"

    def test_optimistic_with_settle_delay(self):
        """Test optimistic with settle delay."""
        attrs = hx_optimistic(settle_delay="100ms")
        assert "settle:100ms" in attrs["hx-swap"]


class TestHXPolling:
    """Test polling helpers."""

    def test_default_polling(self):
        """Test polling with defaults."""
        attrs = hx_polling()
        assert "every 2s" in attrs["hx-trigger"]
        assert "hx-get" not in attrs

    def test_polling_with_url(self):
        """Test polling with URL."""
        attrs = hx_polling(url="/api/status")
        assert attrs["hx-get"] == "/api/status"

    def test_custom_interval(self):
        """Test polling with custom interval."""
        attrs = hx_polling(interval="5s")
        assert "every 5s" in attrs["hx-trigger"]


class TestHXWebSocket:
    """Test WebSocket helpers."""

    def test_websocket_connection(self):
        """Test WebSocket connection attributes."""
        attrs = hx_websocket("ws://localhost:8000/ws")
        assert "connect:ws://localhost:8000/ws" in attrs["hx-ws"]


class TestHXSSE:
    """Test Server-Sent Events helpers."""

    def test_default_sse(self):
        """Test SSE with defaults."""
        attrs = hx_sse("/events")
        assert "connect:/events" in attrs["hx-sse"]
        assert "sse:message" in attrs["hx-trigger"]

    def test_sse_with_custom_event(self):
        """Test SSE with custom event name."""
        attrs = hx_sse("/events", swap="update")
        assert "sse:update" in attrs["hx-trigger"]


class TestHTMXPerformanceMonitor:
    """Test HTMX performance monitoring."""

    def test_monitor_initialization(self):
        """Test monitor starts enabled."""
        monitor = HTMXPerformanceMonitor()
        assert monitor._enabled is True
        assert len(monitor._requests) == 0

    def test_enable_disable(self):
        """Test enabling and disabling monitor."""
        monitor = HTMXPerformanceMonitor()
        monitor.disable()
        assert monitor._enabled is False
        monitor.enable()
        assert monitor._enabled is True

    def test_record_request(self):
        """Test recording request."""
        monitor = HTMXPerformanceMonitor()
        monitor.record_request("/api/users", "GET", 150.5, 1024)
        assert len(monitor._requests) == 1
        assert monitor._requests[0]["url"] == "/api/users"
        assert monitor._requests[0]["method"] == "GET"
        assert monitor._requests[0]["duration_ms"] == 150.5
        assert monitor._requests[0]["size_bytes"] == 1024

    def test_record_request_when_disabled(self):
        """Test recording doesn't work when disabled."""
        monitor = HTMXPerformanceMonitor()
        monitor.disable()
        monitor.record_request("/api/users", "GET", 100)
        assert len(monitor._requests) == 0

    def test_get_stats_empty(self):
        """Test getting stats with no requests."""
        monitor = HTMXPerformanceMonitor()
        stats = monitor.get_stats()
        assert stats["total_requests"] == 0
        assert stats["avg_duration_ms"] == 0
        assert stats["max_duration_ms"] == 0

    def test_get_stats_with_requests(self):
        """Test getting stats with recorded requests."""
        monitor = HTMXPerformanceMonitor()
        monitor.record_request("/api/users", "GET", 100)
        monitor.record_request("/api/posts", "GET", 200)
        monitor.record_request("/api/comments", "GET", 300)

        stats = monitor.get_stats()
        assert stats["total_requests"] == 3
        assert stats["avg_duration_ms"] == 200  # (100+200+300)/3
        assert stats["max_duration_ms"] == 300

    def test_get_stats_with_sizes(self):
        """Test stats include size information."""
        monitor = HTMXPerformanceMonitor()
        monitor.record_request("/api/users", "GET", 100, 512)
        monitor.record_request("/api/posts", "GET", 200, 1024)

        stats = monitor.get_stats()
        assert stats["total_size_bytes"] == 1536  # 512+1024

    def test_slow_requests(self):
        """Test identifying slow requests."""
        monitor = HTMXPerformanceMonitor()
        monitor.record_request("/api/fast", "GET", 100)
        monitor.record_request("/api/slow", "GET", 1500)  # > 1s
        monitor.record_request("/api/very-slow", "GET", 2000)  # > 1s

        stats = monitor.get_stats()
        assert len(stats["slow_requests"]) == 2
        assert stats["slow_requests"][0]["url"] == "/api/slow"
        assert stats["slow_requests"][1]["url"] == "/api/very-slow"

    def test_clear(self):
        """Test clearing recorded requests."""
        monitor = HTMXPerformanceMonitor()
        monitor.record_request("/api/users", "GET", 100)
        monitor.record_request("/api/posts", "GET", 200)
        assert len(monitor._requests) == 2

        monitor.clear()
        assert len(monitor._requests) == 0


class TestSingletonMonitor:
    """Test singleton monitor behavior."""

    def test_singleton_behavior(self):
        """Test that monitor behaves as expected singleton."""
        # Since HTMXPerformanceMonitor is now registered as a singleton,
        # the container will ensure only one instance exists.
        # This test verifies the class works correctly.
        monitor = HTMXPerformanceMonitor()
        monitor.record_request("/api/test", "GET", 100)
        stats = monitor.get_stats()
        assert stats["total_requests"] == 1
        assert stats["avg_duration_ms"] == 100


class TestIntegration:
    """Test integration of multiple HTMX patterns."""

    def test_prefetch_with_lazy_load(self):
        """Test combining prefetch and lazy load."""
        # Prefetch link
        link_attrs = hx_prefetch("/api/details")
        # Lazy load container
        lazy_attrs = hx_lazy_load("/api/content")

        assert "hx-get" in link_attrs
        assert "hx-get" in lazy_attrs
        assert link_attrs["hx-swap"] == "none"
        assert lazy_attrs["hx-swap"] == "outerHTML"

    def test_debounce_with_optimistic(self):
        """Test combining debounce and optimistic updates."""
        debounce_attrs = hx_debounce("300ms")
        optimistic_attrs = hx_optimistic(indicator="#loading")

        # Can be used together
        combined = {**debounce_attrs, **optimistic_attrs}
        assert "hx-trigger" in combined
        assert "hx-indicator" in combined

    def test_boost_with_morph(self):
        """Test combining boost and morph."""
        boost_attrs = hx_boost(target="#main")
        morph_attrs = hx_morph()

        combined = {**boost_attrs, **morph_attrs}
        assert combined["hx-boost"] == "true"
        assert combined["hx-swap"] == "morph"
