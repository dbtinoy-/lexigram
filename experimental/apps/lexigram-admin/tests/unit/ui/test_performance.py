"""Tests for the performance module."""

from time import sleep

from lexigram.ui.config import DebounceConfig
from lexigram.ui.core.zones import Zones
from lexigram.ui.performance.performance import (
    RenderCache,
    RequestCoalescer,
    ResponseOptimizer,
    add_htmx_timing_header,
    debounced_search_attrs,
    infinite_scroll_trigger,
    lazy_load_placeholder,
    measure_render_time,
    optimize_htmx_response,
)


class TestResponseOptimizer:
    """Tests for ResponseOptimizer class."""

    def test_compute_etag(self):
        optimizer = ResponseOptimizer()
        etag = optimizer.compute_etag("Hello World")
        assert len(etag) == 16
        assert etag.isalnum()

    def test_compute_etag_consistent(self):
        optimizer = ResponseOptimizer()
        content = "Test content"
        assert optimizer.compute_etag(content) == optimizer.compute_etag(content)

    def test_compute_etag_differs_for_different_content(self):
        optimizer = ResponseOptimizer()
        etag1 = optimizer.compute_etag("Content A")
        etag2 = optimizer.compute_etag("Content B")
        assert etag1 != etag2

    def test_should_return_304_no_etag(self):
        optimizer = ResponseOptimizer()
        assert optimizer.should_return_304("content", None) is False

    def test_should_return_304_matching(self):
        optimizer = ResponseOptimizer()
        content = "Test content"
        etag = optimizer.compute_etag(content)
        assert optimizer.should_return_304(content, etag) is True

    def test_should_return_304_quoted(self):
        optimizer = ResponseOptimizer()
        content = "Test content"
        etag = optimizer.compute_etag(content)
        assert optimizer.should_return_304(content, f'"{etag}"') is True

    def test_should_return_304_mismatch(self):
        optimizer = ResponseOptimizer()
        assert optimizer.should_return_304("content", "wrong-etag") is False

    def test_optimize_response_normal(self):
        optimizer = ResponseOptimizer()
        content, status, headers = optimize_htmx_response(
            "<div>Test</div>", optimizer=optimizer
        )
        assert content == "<div>Test</div>"
        assert status == 200
        assert "ETag" in headers
        assert headers["Cache-Control"] == "private, no-cache"

    def test_optimize_response_304(self):
        content = "<div>Test</div>"
        optimizer = ResponseOptimizer()
        etag = optimizer.compute_etag(content)

        result, status, _headers = optimizer.optimize_response(content, etag)
        assert result == ""
        assert status == 304


class TestRenderCache:
    """Tests for RenderCache class."""

    def test_cache_miss(self):
        cache = RenderCache()
        assert cache.get("unknown") is None

    def test_cache_set_and_get(self):
        cache = RenderCache()
        cache.set("component", "<div>Cached</div>", param="value")
        result = cache.get("component", param="value")
        assert result == "<div>Cached</div>"

    def test_cache_different_params(self):
        cache = RenderCache()
        cache.set("component", "<div>A</div>", param="a")
        cache.set("component", "<div>B</div>", param="b")

        assert cache.get("component", param="a") == "<div>A</div>"
        assert cache.get("component", param="b") == "<div>B</div>"

    def test_cache_ttl_expiry(self):
        cache = RenderCache(ttl_seconds=0.1)
        cache.set("component", "<div>Cached</div>")

        assert cache.get("component") == "<div>Cached</div>"
        sleep(0.15)
        assert cache.get("component") is None

    def test_cache_invalidate_all(self):
        cache = RenderCache()
        cache.set("comp1", "<div>1</div>")
        cache.set("comp2", "<div>2</div>")

        cache.invalidate()

        assert cache.get("comp1") is None
        assert cache.get("comp2") is None

    def test_cache_invalidate_by_name(self):
        cache = RenderCache()
        cache.set("comp1", "<div>1</div>")
        cache.set("comp2", "<div>2</div>")

        cache.invalidate("comp1")

        assert cache.get("comp1") is None
        assert cache.get("comp2") == "<div>2</div>"

    def test_cache_eviction(self):
        cache = RenderCache(max_size=2)
        cache.set("comp1", "<div>1</div>")
        cache.set("comp2", "<div>2</div>")
        cache.set("comp3", "<div>3</div>")  # Should evict comp1

        assert cache.get("comp1") is None
        assert cache.get("comp2") == "<div>2</div>"
        assert cache.get("comp3") == "<div>3</div>"

    def test_cached_decorator(self):
        cache = RenderCache()
        call_count = 0

        @cache.cached("test_func")
        def render_component(x: int) -> str:
            nonlocal call_count
            call_count += 1
            return f"<div>{x}</div>"

        # First call - cache miss
        result1 = render_component(x=5)
        assert result1 == "<div>5</div>"
        assert call_count == 1

        # Second call - cache hit
        result2 = render_component(x=5)
        assert result2 == "<div>5</div>"
        assert call_count == 1  # Not called again


class TestLazyLoading:
    """Tests for lazy loading utilities."""

    def test_lazy_load_placeholder(self):
        html = lazy_load_placeholder(
            url="/api/data",
            target_id="content",
            trigger="revealed",
        )
        assert 'id="content"' in html
        assert 'hx-get="/api/data"' in html
        assert 'hx-trigger="revealed"' in html

    def test_lazy_load_placeholder_default_trigger(self):
        html = lazy_load_placeholder(url="/api/data", target_id="content")
        assert 'hx-trigger="load"' in html

    def test_lazy_load_placeholder_custom_placeholder(self):
        html = lazy_load_placeholder(
            url="/api/data",
            target_id="content",
            placeholder="<p>Loading...</p>",
        )
        assert "Loading..." in html

    def test_infinite_scroll_trigger(self):
        html = infinite_scroll_trigger(url="/api/next")
        assert 'hx-get="/api/next"' in html
        assert "revealed" in html
        assert Zones.DATA.selector in html


class TestDebounceConfig:
    """Tests for DebounceConfig."""

    def test_default_trigger(self):
        config = DebounceConfig()
        trigger = config.to_trigger()
        assert "input" in trigger
        assert "changed" in trigger
        assert "delay:300ms" in trigger

    def test_custom_delay(self):
        config = DebounceConfig(delay_ms=500)
        trigger = config.to_trigger()
        assert "delay:500ms" in trigger

    def test_no_changed(self):
        config = DebounceConfig(changed=False)
        trigger = config.to_trigger()
        assert "changed" not in trigger

    def test_debounced_search_attrs(self):
        attrs = debounced_search_attrs("/search", delay_ms=200)
        assert attrs["hx-get"] == "/search"
        assert "delay:200ms" in attrs["hx-trigger"]
        assert attrs["hx-target"] == Zones.DATA.selector


class TestRequestCoalescer:
    """Tests for RequestCoalescer."""

    def test_add_and_flush(self):
        coalescer = RequestCoalescer()
        coalescer.add("filter1", "value1")
        coalescer.add("filter2", "value2")

        result = coalescer.flush()
        assert result == {"filter1": "value1", "filter2": "value2"}

    def test_flush_clears(self):
        coalescer = RequestCoalescer()
        coalescer.add("key", "value")
        coalescer.flush()

        assert coalescer.flush() == {}

    def test_last_value_wins(self):
        coalescer = RequestCoalescer()
        coalescer.add("key", "first")
        coalescer.add("key", "second")

        result = coalescer.flush()
        assert result["key"] == "second"


class TestTimingHelpers:
    """Tests for timing helpers."""

    def test_add_htmx_timing_header(self):
        headers = {"Content-Type": "text/html"}
        result = add_htmx_timing_header(headers, 42.5)

        assert result["Server-Timing"] == "render;dur=42.50"
        assert result["Content-Type"] == "text/html"

    def test_measure_render_time_decorator(self):
        @measure_render_time
        def slow_render() -> str:
            sleep(0.01)
            return "<div>Done</div>"

        content, elapsed_ms = slow_render()
        assert content == "<div>Done</div>"
        assert elapsed_ms >= 10
