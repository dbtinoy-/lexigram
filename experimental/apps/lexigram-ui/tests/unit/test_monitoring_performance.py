"""Tests for UI performance module."""

import pytest

from lexigram.ui.performance import performance


class TestResponseOptimizer:
    """Tests for ResponseOptimizer."""

    def test_optimizer_is_dataclass(self) -> None:
        """Test optimizer is a dataclass."""
        opt = performance.ResponseOptimizer()
        assert hasattr(opt, "compute_etag")
        assert hasattr(opt, "should_return_304")

    def test_compute_etag(self) -> None:
        """Test ETag computation."""
        opt = performance.ResponseOptimizer()
        etag = opt.compute_etag("test content")
        assert isinstance(etag, str)
        assert len(etag) == 16

    def test_compute_etag_deterministic(self) -> None:
        """Test ETag is deterministic."""
        opt = performance.ResponseOptimizer()
        etag1 = opt.compute_etag("test content")
        etag2 = opt.compute_etag("test content")
        assert etag1 == etag2

    def test_compute_etag_different_content(self) -> None:
        """Test different content produces different ETags."""
        opt = performance.ResponseOptimizer()
        etag1 = opt.compute_etag("content 1")
        etag2 = opt.compute_etag("content 2")
        assert etag1 != etag2

    def test_should_return_304_no_etag(self) -> None:
        """Test 304 not returned without ETag."""
        opt = performance.ResponseOptimizer()
        result = opt.should_return_304("content", None)
        assert result is False

    def test_should_return_304_matching_etag(self) -> None:
        """Test 304 returned when ETags match."""
        opt = performance.ResponseOptimizer()
        content = "test content"
        etag = opt.compute_etag(content)
        result = opt.should_return_304(content, etag)
        assert result is True

    def test_should_return_304_quoted_etag(self) -> None:
        """Test 304 with quoted ETag."""
        opt = performance.ResponseOptimizer()
        content = "test content"
        etag = opt.compute_etag(content)
        result = opt.should_return_304(content, f'"{etag}"')
        assert result is True

    def test_should_return_304_non_matching(self) -> None:
        """Test 304 not returned when ETags don't match."""
        opt = performance.ResponseOptimizer()
        result = opt.should_return_304("content", "different-etag")
        assert result is False

    def test_optimize_response_304(self) -> None:
        """Test optimize returns 304."""
        opt = performance.ResponseOptimizer()
        content = "test content"
        etag = opt.compute_etag(content)
        result_content, status, headers = opt.optimize_response(content, etag)
        assert status == 304
        assert result_content == ""
        assert "ETag" in headers

    def test_optimize_response_200(self) -> None:
        """Test optimize returns 200 with headers."""
        opt = performance.ResponseOptimizer()
        result_content, status, headers = opt.optimize_response("test content")
        assert status == 200
        assert result_content == "test content"
        assert "ETag" in headers
        assert "Cache-Control" in headers


class TestOptimizeHtmxResponse:
    """Tests for optimize_htmx_response function."""

    def test_no_optimizer(self) -> None:
        """Test returns unchanged when no optimizer."""
        content, status, headers = performance.optimize_htmx_response("test")
        assert status == 200
        assert content == "test"
        assert headers == {}

    def test_with_optimizer(self) -> None:
        """Test returns optimized when optimizer provided."""
        opt = performance.ResponseOptimizer()
        content, status, headers = performance.optimize_htmx_response(
            "test", optimizer=opt
        )
        assert status == 200
        assert "ETag" in headers


class TestRenderCache:
    """Tests for RenderCache."""

    def test_cache_is_dataclass(self) -> None:
        """Test cache is a dataclass."""
        cache = performance.RenderCache()
        assert hasattr(cache, "get")
        assert hasattr(cache, "set")

    def test_get_miss(self) -> None:
        """Test cache miss."""
        cache = performance.RenderCache()
        result = cache.get("test-component", foo="bar")
        assert result is None

    def test_set_and_get(self) -> None:
        """Test cache set and get."""
        cache = performance.RenderCache()
        cache.set("test-component", "<div>Test</div>", foo="bar")
        result = cache.get("test-component", foo="bar")
        assert result == "<div>Test</div>"

    def test_cache_expiry(self) -> None:
        """Test cache expiration."""
        cache = performance.RenderCache()
        import time

        original_ttl = cache.ttl_seconds
        cache.ttl_seconds = 0
        cache.set("test-component", "<div>Test</div>")
        time.sleep(0.01)
        result = cache.get("test-component")
        cache.ttl_seconds = original_ttl
        assert result is None

    def test_invalidate_all(self) -> None:
        """Test invalidate all."""
        cache = performance.RenderCache()
        cache.set("comp1", "content1")
        cache.set("comp2", "content2")
        cache.invalidate()
        assert cache.get("comp1") is None
        assert cache.get("comp2") is None

    def test_invalidate_by_name(self) -> None:
        """Test invalidate by component name."""
        cache = performance.RenderCache()
        cache.set("component", "content1")
        cache.set("other", "content2")
        cache.invalidate("component")
        assert cache.get("component") is None
        assert cache.get("other") == "content2"

    def test_max_size_eviction(self) -> None:
        """Test max size eviction."""
        cache = performance.RenderCache()
        cache.max_size = 2
        cache.set("comp1", "content1")
        cache.set("comp2", "content2")
        cache.set("comp3", "content3")
        assert cache.get("comp1") is None
        assert cache.get("comp2") == "content2"


class TestCachedDecorator:
    """Tests for cached decorator."""

    def test_cached_decorator(self) -> None:
        """Test cached decorator wraps function."""
        cache = performance.RenderCache()

        @cache.cached()
        def render_component() -> str:
            return "<div>Rendered</div>"

        result = render_component()
        assert result == "<div>Rendered</div>"

    def test_cached_with_args(self) -> None:
        """Test cached decorator with arguments."""
        cache = performance.RenderCache()

        @cache.cached()
        def render_component(id: int) -> str:
            return f"<div>{id}</div>"

        result = render_component(1)
        assert result == "<div>1</div>"


class TestDebouncedSearchAttrs:
    """Tests for debounced_search_attrs."""

    def test_default_delay(self) -> None:
        """Test default delay."""
        attrs = performance.debounced_search_attrs("/search")
        assert attrs["hx-get"] == "/search"
        assert "hx-trigger" in attrs

    def test_custom_delay(self) -> None:
        """Test custom delay."""
        attrs = performance.debounced_search_attrs("/search", delay_ms=500)
        assert attrs["hx-get"] == "/search"

    def test_custom_target(self) -> None:
        """Test custom target."""
        attrs = performance.debounced_search_attrs("/search", target="#results")
        assert attrs["hx-target"] == "#results"


class TestRequestCoalescer:
    """Tests for RequestCoalescer."""

    def test_add_pending(self) -> None:
        """Test adding pending values."""
        coalescer = performance.RequestCoalescer()
        coalescer.add("key1", "value1")
        assert coalescer.pending["key1"] == "value1"

    def test_flush(self) -> None:
        """Test flush returns and clears."""
        coalescer = performance.RequestCoalescer()
        coalescer.add("key1", "value1")
        result = coalescer.flush()
        assert result == {"key1": "value1"}
        assert coalescer.pending == {}


class TestTimingHeaders:
    """Tests for timing header helpers."""

    def test_add_timing_header(self) -> None:
        """Test adding timing header."""
        headers = performance.add_htmx_timing_header({}, 10.5)
        assert "Server-Timing" in headers
        assert "render" in headers["Server-Timing"]

    def test_measure_render_time(self) -> None:
        """Test measure render time decorator."""
        decorated = performance.measure_render_time(lambda: "result")
        result, duration = decorated()
        assert result == "result"
        assert duration > 0


class TestLazyLoad:
    """Tests for lazy load functions."""

    def test_lazy_load_placeholder(self) -> None:
        """Test lazy load placeholder."""
        html = performance.lazy_load_placeholder("/load", "target-id")
        assert 'id="target-id"' in html
        assert "hx-get" in html

    def test_lazy_load_custom_trigger(self) -> None:
        """Test custom trigger."""
        html = performance.lazy_load_placeholder("/load", "target-id", trigger="revealed")
        assert "revealed" in html

    def test_infinite_scroll_trigger(self) -> None:
        """Test infinite scroll trigger."""
        html = performance.infinite_scroll_trigger("/load")
        assert "hx-get" in html
        assert "revealed" in html


class TestPerformanceExports:
    """Tests for performance module exports."""

    def test_response_optimizer_exported(self) -> None:
        """Test ResponseOptimizer is exported."""
        from lexigram.ui.performance import performance

        assert hasattr(performance, "ResponseOptimizer")

    def test_render_cache_exported(self) -> None:
        """Test RenderCache is exported."""
        from lexigram.ui.performance import performance

        assert hasattr(performance, "RenderCache")